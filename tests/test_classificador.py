import unittest
from dataclasses import replace

from src.classificador_fadiga import ClassificadorFadiga, ParametrosClassificador


def indicadores(**valores):
    base = {
        "estado": "ATENTO", "olhos_fechados": False, "tempo_olho_fechado": 0.0,
        "bocejo": False, "movimento_cabeca": False, "perclos": None,
        "perclos_valido": False, "perclos_cobertura": None,
        "frequencia_fechamentos_prolongados": 0, "frequencia_bocejos": 0,
        "frequencia_movimentos": 0,
    }
    base.update(valores)
    return base


class ClassificadorTests(unittest.TestCase):
    def criar(self, **alteracoes):
        parametros = ParametrosClassificador(
            janela_evento_olhos=6.0, janela_evento_boca=6.0, janela_evento_cabeca=4.0,
            persistencia_entrada_atencao=0.5, persistencia_saida_atencao=1.0,
            persistencia_entrada_fadiga=1.0, persistencia_saida_fadiga=1.0,
        )
        return ClassificadorFadiga(parametros=replace(parametros, **alteracoes))

    def evento(self, inicio, fim=None, duracao=1.0, forca=1.0, confirmado=True):
        return {"inicio": inicio, "fim": inicio + duracao if fim is None else fim,
                "duracao": duracao, "forca": forca, "confirmado": confirmado}

    def iniciar(self, classificador):
        self.assertEqual(classificador.atualizar(indicadores(estado="CALIBRANDO"), 0.0), "CALIBRANDO")

    def tornar_atento(self, classificador):
        self.iniciar(classificador)
        self.assertEqual(classificador.atualizar(indicadores(), 0.0), "CALIBRANDO")
        self.assertEqual(classificador.atualizar(indicadores(), 0.6), "ATENTO")

    def test_api_legada_continua_aceitando_parametros(self):
        classificador = ClassificadorFadiga(
            janela_analise=30.0, tempo_minimo_atencao=1.0, tempo_minimo_fadiga=2.0,
            persistencia_transicao=0.25, minimo_evidencias_fadiga=2,
            minimo_fechamentos_prolongados=1, minimo_bocejos=1,
            minimo_movimentos_cabeca=1)
        self.assertEqual(classificador.janela_analise, 30.0)
        self.assertEqual(classificador.tempo_minimo_atencao, 1.0)

    def test_diagnostico_expoe_motivo_e_persistencia_sem_alterar_estado(self):
        classificador = self.criar()
        classificador.atualizar(
            indicadores(eventos={"olhos": [self.evento(0.0, duracao=2.0)]}),
            0.0,
        )

        self.assertEqual(classificador.diagnostico["motivo_classificacao"], "olhos")
        self.assertTrue(classificador.diagnostico["sinal_atencao"])
        self.assertEqual(
            classificador.diagnostico["persistencia_fadiga_necessaria"],
            classificador.parametros.persistencia_entrada_fadiga,
        )

    def test_evento_isolado_e_decaimento_temporal(self):
        classificador = self.criar()
        self.iniciar(classificador)
        sinais = indicadores(eventos={"olhos": [self.evento(0.0, duracao=2.0)]})
        classificador.atualizar(sinais, 0.0)
        self.assertEqual(classificador.escores["olhos"], 1.0)
        self.assertEqual(classificador.atualizar(sinais, 0.6), "ATENCAO")
        classificador.atualizar(sinais, 3.0)
        # O evento terminou em t=2; em t=3 a idade e 1 segundo.
        self.assertAlmostEqual(classificador.escores["olhos"], 5 / 6, places=6)
        classificador.atualizar(sinais, 8.1)
        self.assertEqual(classificador.escores["olhos"], 0.0)

    def test_sinal_instantaneo_nao_permanece_apos_interrupcao(self):
        classificador = self.criar()
        self.tornar_atento(classificador)
        classificador.atualizar(indicadores(olhos_fechados=True, tempo_olho_fechado=2.0), 1.0)
        self.assertEqual(classificador.escores["olhos"], 1.0)
        classificador.atualizar(indicadores(), 1.1)
        self.assertEqual(classificador.escores["olhos"], 0.0)

    def test_dois_eventos_proximos_de_categorias_diferentes(self):
        classificador = self.criar()
        self.iniciar(classificador)
        sinais = indicadores(
            eventos={"olhos": [self.evento(0.0, duracao=2.0)],
                     "boca": [self.evento(0.0, duracao=1.0)]},
            frequencia_bocejos=2,
        )
        classificador.atualizar(sinais, 0.0)
        self.assertEqual(classificador.categorias_significativas, 2)
        self.assertGreaterEqual(classificador.escore_total, 0.5)

    def test_eventos_distantes_nao_formam_combinacao(self):
        classificador = self.criar()
        self.tornar_atento(classificador)
        sinais = indicadores(
            eventos={"olhos": [self.evento(0.0, duracao=2.0)],
                     "boca": [self.evento(0.0, duracao=1.0)]},
            frequencia_bocejos=2,
        )
        classificador.atualizar(sinais, 0.0)
        classificador.atualizar(sinais, 6.1)
        self.assertEqual(classificador.categorias_significativas, 0)
        self.assertLess(classificador.escore_total, 0.5)

    def test_duas_categorias_significativas_permitam_fadiga(self):
        classificador = self.criar()
        self.iniciar(classificador)
        sinais = indicadores(
            eventos={"olhos": [self.evento(0.0, duracao=2.0)],
                     "boca": [self.evento(0.0, duracao=1.0)]},
            frequencia_bocejos=2,
        )
        self.assertEqual(classificador.atualizar(sinais, 0.0), "CALIBRANDO")
        self.assertEqual(classificador.atualizar(sinais, 0.6), "ATENCAO")
        self.assertEqual(classificador.atualizar(sinais, 0.9), "ATENCAO")
        self.assertEqual(classificador.atualizar(sinais, 1.1), "FADIGA")

    def test_somente_uma_categoria_significativa_nao_entra_em_fadiga(self):
        classificador = self.criar()
        self.tornar_atento(classificador)
        sinais = indicadores(eventos={"olhos": [self.evento(1.0, duracao=2.0)]})
        classificador.atualizar(sinais, 1.0)
        classificador.atualizar(sinais, 3.0)
        self.assertNotEqual(classificador.estado_atual, "FADIGA")
        self.assertEqual(classificador.categorias_significativas, 1)

    def test_um_indicador_prolongado_pode_entrar_em_fadiga_individual(self):
        classificador = self.criar()
        self.tornar_atento(classificador)
        sinais = indicadores(olhos_fechados=True, tempo_olho_fechado=2.0)
        classificador.atualizar(sinais, 0.6)
        self.assertNotEqual(classificador.estado_atual, "FADIGA")
        self.assertEqual(classificador.atualizar(sinais, 4.7), "FADIGA")
        self.assertEqual(classificador.diagnostico["modo_fadiga"], "INDIVIDUAL")
        self.assertEqual(classificador.diagnostico["fatores_fadiga"], ["olhos"])

    def test_cabeca_prolongada_tem_evidencia_individual(self):
        classificador = self.criar()
        self.tornar_atento(classificador)
        sinais = indicadores(
            movimento_cabeca=True,
            tempo_movimento_cabeca=2.0,
        )
        classificador.atualizar(sinais, 0.6)
        self.assertEqual(classificador.atualizar(sinais, 4.7), "FADIGA")
        self.assertEqual(classificador.diagnostico["fatores_fadiga"], ["cabeca"])

    def test_um_bocejo_nao_gera_fadiga_individual(self):
        classificador = self.criar()
        self.tornar_atento(classificador)
        sinais = indicadores(bocejo=True, frequencia_bocejos=1)
        classificador.atualizar(sinais, 0.6)
        classificador.atualizar(sinais, 5.0)
        self.assertNotEqual(classificador.estado_atual, "FADIGA")

    def test_boca_aberta_e_avaliada_antes_de_fechar(self):
        classificador = self.criar()
        self.tornar_atento(classificador)
        sinais = indicadores(
            boca_aberta=True,
            tempo_boca_aberta=0.8,
            frequencia_bocejos=0,
        )
        classificador.atualizar(sinais, 0.6)
        self.assertGreater(classificador.escores["boca"], 0.0)

    def test_entrada_e_saida_de_atencao_com_persistencia(self):
        classificador = self.criar()
        self.tornar_atento(classificador)
        evento = indicadores(
            eventos={"boca": [self.evento(1.0, fim=1.0, duracao=1.0)]},
            frequencia_bocejos=2,
        )
        self.assertEqual(classificador.atualizar(evento, 1.0), "ATENTO")
        self.assertEqual(classificador.atualizar(evento, 1.5), "ATENCAO")
        vazio = indicadores()
        self.assertEqual(classificador.atualizar(vazio, 6.1), "ATENCAO")
        self.assertEqual(classificador.atualizar(vazio, 7.2), "ATENTO")

    def test_entrada_e_saida_de_fadiga_com_histerese(self):
        classificador = self.criar()
        self.iniciar(classificador)
        sinais = indicadores(
            eventos={"olhos": [self.evento(0.0, duracao=2.0)],
                     "boca": [self.evento(0.0, duracao=1.0)]},
            frequencia_bocejos=2,
        )
        classificador.atualizar(sinais, 0.0)
        classificador.atualizar(sinais, 0.6)
        self.assertEqual(classificador.atualizar(sinais, 1.7), "FADIGA")
        self.assertEqual(classificador.atualizar(sinais, 2.0), "FADIGA")
        vazio = indicadores()
        self.assertEqual(classificador.atualizar(vazio, 2.1), "FADIGA")
        self.assertEqual(classificador.atualizar(vazio, 3.2), "ATENTO")

    def test_sem_rosto_e_calibrando_tem_prioridade_e_resetam_historico(self):
        classificador = self.criar()
        self.assertEqual(classificador.atualizar(indicadores(estado="CALIBRANDO"), 0.0), "CALIBRANDO")
        self.assertEqual(classificador.atualizar(indicadores(estado="SEM_ROSTO"), 1.0), "SEM_ROSTO")
        self.assertEqual(classificador.atualizar(indicadores(), 1.1), "SEM_ROSTO")
        self.assertEqual(classificador.atualizar(indicadores(estado="CALIBRANDO"), 1.2), "CALIBRANDO")
        self.assertEqual(classificador.atualizar(indicadores(), 1.3), "CALIBRANDO")

    def test_perclos_invalido_e_desabilitado_nao_contribui(self):
        desabilitado = self.criar()
        self.tornar_atento(desabilitado)
        sinais = indicadores(perclos=0.8, perclos_valido=True, perclos_cobertura=1.0)
        desabilitado.atualizar(sinais, 1.0)
        self.assertEqual(desabilitado.escores["olhos"], 0.0)

        habilitado = self.criar(perclos_minimo=0.30)
        self.tornar_atento(habilitado)
        invalido = indicadores(perclos=0.8, perclos_valido=True, perclos_cobertura=0.5)
        habilitado.atualizar(invalido, 1.0)
        self.assertEqual(habilitado.escores["olhos"], 0.0)
        valido = indicadores(perclos=0.8, perclos_valido=True, perclos_cobertura=0.9)
        habilitado.atualizar(valido, 1.1)
        self.assertGreater(habilitado.escores["olhos"], 0.0)


if __name__ == "__main__":
    unittest.main()
