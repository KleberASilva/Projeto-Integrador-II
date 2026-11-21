import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.telemetria import Telemetria


class TelemetriaTests(unittest.TestCase):
    def test_cria_arquivos_por_sessao_e_preserva_evento(self):
        with tempfile.TemporaryDirectory() as pasta:
            primeiro = Telemetria(
                pasta=pasta, session_id="sessao_a", agora=100.0
            )
            evento = {
                "tipo": "FECHAMENTO_PROLONGADO",
                "inicio": 101.0,
                "fim": 102.5,
                "duracao": 1.5,
                "confirmado": True,
                "motivo": None,
            }
            primeiro.registrar(
                {"estado": "ATENCAO", "evento_olhos": evento},
                frame=7,
                agora=102.5,
            )
            primeiro.registrar(
                {"estado": "ATENCAO", "evento_olhos": evento},
                frame=8,
                agora=102.6,
            )
            primeiro.fechar()

            segundo = Telemetria(
                pasta=pasta, session_id="sessao_b", agora=200.0
            )
            segundo.registrar(
                {"estado": "CALIBRANDO"}, frame=1, agora=200.1
            )
            segundo.fechar()

            arquivos = sorted(Path(pasta).glob("**/*.csv"))
            self.assertEqual(len(arquivos), 4)

            with open(
                Path(pasta) / "sessao_a" / "eventos.csv",
                newline="",
                encoding="utf-8",
            ) as arquivo:
                eventos = list(csv.DictReader(arquivo))
            self.assertEqual(len(eventos), 1)
            self.assertEqual(eventos[0]["tipo"], "FECHAMENTO_PROLONGADO")
            self.assertEqual(eventos[0]["inicio_monotonic"], "101.0")
            self.assertEqual(eventos[0]["fim_monotonic"], "102.5")
            self.assertEqual(eventos[0]["duracao"], "1.5")
            self.assertEqual(eventos[0]["confirmado"], "True")

            with open(
                Path(pasta) / "sessao_a" / "telemetria.csv",
                newline="",
                encoding="utf-8",
            ) as arquivo:
                medicoes = list(csv.DictReader(arquivo))
            self.assertEqual(len(medicoes), 2)
            self.assertEqual(medicoes[0]["session_id"], "sessao_a")
            self.assertEqual(medicoes[0]["frame"], "7")
            self.assertEqual(
                medicoes[0]["evento_olhos"], "FECHAMENTO_PROLONGADO"
            )

    def test_marcacao_manual_tem_timestamp_e_duracao_zero(self):
        with tempfile.TemporaryDirectory() as pasta:
            telemetria = Telemetria(
                pasta=pasta, session_id="manual", agora=10.0
            )
            telemetria.registrar_marcacao(
                "ROTACAO_ESQUERDA",
                "Teste manual",
                frame=3,
                agora=12.0,
            )
            telemetria.fechar()

            with open(
                Path(pasta) / "manual" / "eventos.csv",
                newline="",
                encoding="utf-8",
            ) as arquivo:
                evento = next(csv.DictReader(arquivo))
            self.assertEqual(evento["origem"], "manual")
            self.assertEqual(evento["descricao"], "Teste manual")
            self.assertEqual(evento["duracao"], "0.0")
            self.assertEqual(evento["frame_inicio"], "3")
            self.assertTrue(evento["inicio_timestamp"])
            self.assertTrue(evento["fim_timestamp"])

    def test_captura_fica_na_sessao_e_na_mesma_linha_do_frame(self):
        with tempfile.TemporaryDirectory() as pasta:
            telemetria = Telemetria(
                pasta=pasta, session_id="captura", agora=10.0
            )
            caminho = telemetria.registrar(
                {
                    "estado": "ATENCAO",
                    "estado_olhos": "ABERTOS",
                    "estado_boca": "FECHADA",
                    "estado_cabeca": "NORMAL",
                    "escore_olhos": 0.2,
                    "escore_boca": 0.4,
                    "escore_cabeca": 0.0,
                    "escore_total": 0.23,
                    "peso_olhos": 0.45,
                    "peso_boca": 0.35,
                    "peso_cabeca": 0.20,
                    "motivo_classificacao": "boca",
                },
                frame=123,
                agora=12.0,
                imagem=np.zeros((40, 60, 3), dtype=np.uint8),
            )
            telemetria.fechar()

            self.assertTrue(caminho.startswith("capturas/"))
            captura = Path(pasta) / "captura" / caminho
            self.assertTrue(captura.exists())

            with open(
                Path(pasta) / "captura" / "telemetria.csv",
                newline="",
                encoding="utf-8",
            ) as arquivo:
                medicao = next(csv.DictReader(arquivo))
            self.assertEqual(medicao["frame"], "123")
            self.assertEqual(medicao["captura_arquivo"], caminho)
            self.assertEqual(medicao["escore_total"], "0.23")


if __name__ == "__main__":
    unittest.main()
