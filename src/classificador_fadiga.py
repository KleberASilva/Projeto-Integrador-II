"""Classificacao temporal e experimental de indicadores de fadiga.

Os escores produzidos por este modulo sao indices normalizados de evidencia,
nao probabilidades e nao sao limiares fisiologicamente validados.
"""

from collections import deque
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class ParametrosClassificador:
    """Parametros de prototipo; todos exigem validacao experimental."""

    janela_analise: float = 60.0
    janela_evento_olhos: float = 15.0
    janela_evento_boca: float = 20.0
    janela_evento_cabeca: float = 10.0
    tempo_referencia_olhos: float = 2.0
    tempo_referencia_boca: float = 1.0
    tempo_referencia_cabeca: float = 1.5
    peso_olhos: float = 0.45
    peso_boca: float = 0.35
    peso_cabeca: float = 0.20
    limiar_atencao: float = 0.25
    limiar_saida_atencao: float = 0.15
    limiar_fadiga: float = 0.50
    limiar_saida_fadiga: float = 0.30
    limiar_categoria_significativa: float = 0.35
    persistencia_entrada_atencao: float = 0.5
    persistencia_saida_atencao: float = 1.0
    persistencia_entrada_fadiga: float = 2.0
    persistencia_saida_fadiga: float = 1.5
    perclos_minimo: float | None = None
    perclos_referencia: float = 0.30
    perclos_cobertura_minima: float = 0.80
    minimo_fechamentos_prolongados: int = 2
    minimo_bocejos: int = 2
    minimo_movimentos_cabeca: int = 2


def _limitar(valor, minimo=0.0, maximo=1.0):
    return max(minimo, min(maximo, float(valor)))


class ClassificadorFadiga:
    """Combina sinais instantaneos e eventos recentes com histerese temporal."""

    def __init__(
        self,
        parametros=None,
        janela_analise=None,
        tempo_minimo_atencao=None,
        tempo_minimo_fadiga=None,
        persistencia_transicao=None,
        minimo_evidencias_fadiga=None,
        minimo_fechamentos_prolongados=None,
        minimo_bocejos=None,
        minimo_movimentos_cabeca=None,
        perclos_minimo=None,
    ):
        base = parametros or ParametrosClassificador()
        if not isinstance(base, ParametrosClassificador):
            raise TypeError("parametros deve ser ParametrosClassificador")
        overrides = {}
        if janela_analise is not None:
            overrides["janela_analise"] = janela_analise
        if tempo_minimo_atencao is not None:
            overrides["tempo_referencia_olhos"] = tempo_minimo_atencao
        if tempo_minimo_fadiga is not None:
            overrides["persistencia_entrada_fadiga"] = tempo_minimo_fadiga
        if persistencia_transicao is not None:
            overrides["persistencia_entrada_atencao"] = persistencia_transicao
            overrides["persistencia_saida_atencao"] = persistencia_transicao
        if minimo_fechamentos_prolongados is not None:
            overrides["minimo_fechamentos_prolongados"] = minimo_fechamentos_prolongados
        if minimo_bocejos is not None:
            overrides["minimo_bocejos"] = minimo_bocejos
        if minimo_movimentos_cabeca is not None:
            overrides["minimo_movimentos_cabeca"] = minimo_movimentos_cabeca
        if perclos_minimo is not None:
            overrides["perclos_minimo"] = perclos_minimo
        self.parametros = replace(base, **overrides)

        # Atributos legados preservados para callers existentes.
        self.janela_analise = self.parametros.janela_analise
        self.tempo_minimo_atencao = self.parametros.tempo_referencia_olhos
        self.tempo_minimo_fadiga = self.parametros.persistencia_entrada_fadiga
        self.persistencia_transicao = self.parametros.persistencia_entrada_atencao
        self.minimo_evidencias_fadiga = 2 if minimo_evidencias_fadiga is None else minimo_evidencias_fadiga
        self.minimo_fechamentos_prolongados = self.parametros.minimo_fechamentos_prolongados
        self.minimo_bocejos = self.parametros.minimo_bocejos
        self.minimo_movimentos_cabeca = self.parametros.minimo_movimentos_cabeca
        self.perclos_minimo = self.parametros.perclos_minimo

        self.historico_indicadores = deque()
        self.estado_atual = "CALIBRANDO"
        self.ultimo_tempo = None
        self.escores = {"olhos": 0.0, "boca": 0.0, "cabeca": 0.0}
        self.escore_total = 0.0
        self.categorias_significativas = 0
        self._candidato = None
        self._inicio_candidato = None
        self._inicio_evidencia_fadiga = None
        self._ultima_frequencia = {"olhos": 0, "boca": 0, "cabeca": 0}
        self._inicio_frequencia = {"olhos": None, "boca": None, "cabeca": None}
        self.diagnostico = {}

    def _registrar_indicadores(self, indicadores, agora):
        self.historico_indicadores.append({"tempo": agora, **indicadores})
        limite = agora - self.janela_analise
        while self.historico_indicadores and self.historico_indicadores[0]["tempo"] < limite:
            self.historico_indicadores.popleft()

    def _eventos(self, indicadores, categoria):
        todos = indicadores.get("eventos", {}) or {}
        eventos = todos.get(categoria, []) if isinstance(todos, dict) else []
        if not isinstance(eventos, (list, tuple)):
            eventos = [eventos]
        singular = indicadores.get("evento_" + categoria)
        if singular:
            eventos = [*eventos, singular]
        aliases = indicadores.get("eventos_" + categoria)
        if aliases:
            eventos = [*eventos, *aliases] if isinstance(aliases, (list, tuple)) else [*eventos, aliases]
        return eventos

    def _escore_eventos(self, indicadores, categoria, agora, janela, referencia):
        melhor = 0.0
        for evento in self._eventos(indicadores, categoria):
            if not isinstance(evento, dict) or evento.get("confirmado", True) is False:
                continue
            fim = evento.get("fim", agora)
            inicio = evento.get("inicio", fim)
            duracao = evento.get("duracao")
            if duracao is None:
                duracao = max(0.0, float(fim) - float(inicio))
            idade = max(0.0, float(agora) - float(fim))
            decaimento = max(0.0, 1.0 - idade / janela) if janela > 0 else 0.0
            forca = _limitar(evento.get("forca", 1.0))
            intensidade_duracao = 1.0 if duracao <= 0 else _limitar(duracao / referencia)
            melhor = max(melhor, forca * intensidade_duracao * decaimento)
        return melhor

    def _frequencia_legada(self, indicadores, categoria, agora, chave, minimo, janela):
        """Fallback para o contrato atual do monitoramento, sem inventar idades."""
        valor = max(0, int(indicadores.get(chave, 0) or 0))
        anterior = self._ultima_frequencia[categoria]
        if valor > anterior or (valor and self._inicio_frequencia[categoria] is None):
            self._inicio_frequencia[categoria] = agora
        elif valor == 0:
            self._inicio_frequencia[categoria] = None
        self._ultima_frequencia[categoria] = valor
        inicio = self._inicio_frequencia[categoria]
        if not valor or inicio is None:
            return 0.0
        idade = max(0.0, agora - inicio)
        decaimento = max(0.0, 1.0 - idade / janela) if janela > 0 else 0.0
        return _limitar(valor / max(1, minimo)) * decaimento

    def _calcular_escores(self, indicadores, agora):
        p = self.parametros
        olhos = 0.0
        if indicadores.get("olhos_fechados"):
            olhos = _limitar((indicadores.get("tempo_olho_fechado") or 0.0) / p.tempo_referencia_olhos)
        boca = 1.0 if indicadores.get("bocejo") else 0.0
        if indicadores.get("boca_aberta"):
            boca = max(boca, _limitar((indicadores.get("tempo_boca_aberta") or 0.0) / p.tempo_referencia_boca))
        cabeca = 0.0
        if indicadores.get("movimento_cabeca"):
            cabeca = _limitar((indicadores.get("tempo_movimento_cabeca") or p.tempo_referencia_cabeca) / p.tempo_referencia_cabeca)
            cabeca *= _limitar(indicadores.get("intensidade_cabeca", 1.0))

        olhos = max(olhos, self._escore_eventos(indicadores, "olhos", agora, p.janela_evento_olhos, p.tempo_referencia_olhos))
        boca = max(boca, self._escore_eventos(indicadores, "boca", agora, p.janela_evento_boca, p.tempo_referencia_boca))
        cabeca = max(cabeca, self._escore_eventos(indicadores, "cabeca", agora, p.janela_evento_cabeca, p.tempo_referencia_cabeca))
        olhos = max(olhos, self._frequencia_legada(indicadores, "olhos", agora, "frequencia_fechamentos_prolongados", p.minimo_fechamentos_prolongados, p.janela_evento_olhos))
        boca = max(boca, self._frequencia_legada(indicadores, "boca", agora, "frequencia_bocejos", p.minimo_bocejos, p.janela_evento_boca))
        cabeca = max(cabeca, self._frequencia_legada(indicadores, "cabeca", agora, "frequencia_movimentos", p.minimo_movimentos_cabeca, p.janela_evento_cabeca))

        perclos = indicadores.get("perclos")
        cobertura = indicadores.get("perclos_cobertura")
        perclos_ok = (
            p.perclos_minimo is not None
            and indicadores.get("perclos_valido", False)
            and perclos is not None
            and cobertura is not None
            and cobertura >= p.perclos_cobertura_minima
            and perclos >= p.perclos_minimo
        )
        if perclos_ok:
            olhos = max(olhos, _limitar(perclos / p.perclos_referencia))

        self.escores = {"olhos": _limitar(olhos), "boca": _limitar(boca), "cabeca": _limitar(cabeca)}
        self.escore_total = sum((
            p.peso_olhos * self.escores["olhos"],
            p.peso_boca * self.escores["boca"],
            p.peso_cabeca * self.escores["cabeca"],
        ))
        self.categorias_significativas = sum(score >= p.limiar_categoria_significativa for score in self.escores.values())

    def _limpar_transicao(self):
        self._candidato = None
        self._inicio_candidato = None

    def _transicionar(self, desejado, agora):
        if desejado == self.estado_atual:
            self._limpar_transicao()
            return self.estado_atual
        # A persistencia da evidencia de FADIGA ja foi validada pelo chamador.
        # Nao aplicar uma segunda permanencia de transicao nesse caso.
        if desejado == "FADIGA":
            self.estado_atual = desejado
            self._limpar_transicao()
            return self.estado_atual
        if desejado != self._candidato:
            self._candidato = desejado
            self._inicio_candidato = agora
            return self.estado_atual
        permanencia = agora - self._inicio_candidato
        if self.estado_atual == "FADIGA" and desejado != "FADIGA":
            requerida = self.parametros.persistencia_saida_fadiga
        elif self.estado_atual == "ATENCAO" and desejado == "ATENTO":
            requerida = self.parametros.persistencia_saida_atencao
        elif desejado == "FADIGA":
            requerida = 0.0
        else:
            requerida = self.parametros.persistencia_entrada_atencao
        if permanencia >= requerida:
            self.estado_atual = desejado
            self._limpar_transicao()
        return self.estado_atual

    def atualizar(self, indicadores, agora):
        estado_entrada = indicadores.get("estado")
        if estado_entrada in {"SEM_ROSTO", "CALIBRANDO"}:
            self.historico_indicadores.clear()
            self._limpar_transicao()
            self._inicio_evidencia_fadiga = None
            self.escores = {"olhos": 0.0, "boca": 0.0, "cabeca": 0.0}
            self.escore_total = 0.0
            self.categorias_significativas = 0
            self.estado_atual = estado_entrada
            self.ultimo_tempo = agora
            self.diagnostico = {
                "estado_desejado": estado_entrada,
                "motivo_classificacao": estado_entrada,
                "sinal_atencao": False,
                "sinal_fadiga": False,
                "fadiga_persistente": False,
                "persistencia_fadiga_decorrida": 0.0,
                "persistencia_fadiga_necessaria": self.parametros.persistencia_entrada_fadiga,
                "persistencia_transicao_decorrida": 0.0,
                "persistencia_transicao_necessaria": 0.0,
                "candidato_transicao": None,
            }
            return self.estado_atual

        self._registrar_indicadores(indicadores, agora)
        self._calcular_escores(indicadores, agora)
        p = self.parametros
        fadiga_sinal = self.escore_total >= p.limiar_fadiga and self.categorias_significativas >= 2
        if fadiga_sinal:
            if self._inicio_evidencia_fadiga is None:
                self._inicio_evidencia_fadiga = agora
        else:
            self._inicio_evidencia_fadiga = None
        fadiga_persistente = fadiga_sinal and agora - self._inicio_evidencia_fadiga >= p.persistencia_entrada_fadiga

        atencao_sinal = self.escore_total >= p.limiar_atencao or self.categorias_significativas > 0
        if self.estado_atual == "FADIGA":
            if self.escore_total >= p.limiar_saida_fadiga and self.categorias_significativas >= 2:
                desejado = "FADIGA"
            elif self.escore_total >= p.limiar_saida_atencao or self.categorias_significativas:
                desejado = "ATENCAO"
            else:
                desejado = "ATENTO"
        elif fadiga_persistente:
            desejado = "FADIGA"
        elif self.estado_atual == "ATENCAO":
            desejado = "ATENCAO" if self.escore_total >= p.limiar_saida_atencao or self.categorias_significativas else "ATENTO"
        else:
            desejado = "ATENCAO" if atencao_sinal else "ATENTO"

        persistencia_fadiga_decorrida = (
            0.0 if self._inicio_evidencia_fadiga is None
            else max(0.0, agora - self._inicio_evidencia_fadiga)
        )
        if desejado == "FADIGA":
            persistencia_transicao_necessaria = 0.0
        elif self.estado_atual == "FADIGA":
            persistencia_transicao_necessaria = p.persistencia_saida_fadiga
        elif self.estado_atual == "ATENCAO" and desejado == "ATENTO":
            persistencia_transicao_necessaria = p.persistencia_saida_atencao
        else:
            persistencia_transicao_necessaria = p.persistencia_entrada_atencao
        persistencia_transicao_decorrida = (
            0.0 if self._candidato != desejado or self._inicio_candidato is None
            else max(0.0, agora - self._inicio_candidato)
        )
        motivos = []
        if self.escores["olhos"] >= p.limiar_categoria_significativa:
            motivos.append("olhos")
        if self.escores["boca"] >= p.limiar_categoria_significativa:
            motivos.append("boca")
        if self.escores["cabeca"] >= p.limiar_categoria_significativa:
            motivos.append("cabeca")
        self.diagnostico = {
            "estado_desejado": desejado,
            "motivo_classificacao": ",".join(motivos) or "sem_indicador_significativo",
            "sinal_atencao": atencao_sinal,
            "sinal_fadiga": fadiga_sinal,
            "fadiga_persistente": fadiga_persistente,
            "persistencia_fadiga_decorrida": persistencia_fadiga_decorrida,
            "persistencia_fadiga_necessaria": p.persistencia_entrada_fadiga,
            "persistencia_transicao_decorrida": persistencia_transicao_decorrida,
            "persistencia_transicao_necessaria": persistencia_transicao_necessaria,
            "candidato_transicao": self._candidato,
        }
        self.ultimo_tempo = agora
        return self._transicionar(desejado, agora)
