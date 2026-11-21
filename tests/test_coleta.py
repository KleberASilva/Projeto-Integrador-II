import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np


SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from monitoramento import MonitoramentoThread
from telemetria import Telemetria


class ColetaTests(unittest.TestCase):
    def test_coleta_so_cria_e_fecha_sessao_quando_solicitada(self):
        with tempfile.TemporaryDirectory() as pasta:
            criar_telemetria = lambda: Telemetria(
                pasta=pasta, session_id="sessao_teste", agora=10.0
            )
            thread = MonitoramentoThread()

            with patch("monitoramento.Telemetria", side_effect=criar_telemetria):
                thread._atualizar_coleta()
                self.assertFalse(thread._coleta_ativa)
                self.assertIsNone(thread.telemetria)

                thread.iniciar_coleta()
                thread._atualizar_coleta()
                self.assertTrue(thread._coleta_ativa)
                self.assertIsNotNone(thread.telemetria)

                thread._registrar_frame(
                    {"estado": "ATENTO"},
                    np.zeros((20, 20, 3), dtype=np.uint8),
                    1,
                    10.1,
                )
                self.assertTrue(
                    (Path(pasta) / "sessao_teste" / "telemetria.csv").exists()
                )

                thread.parar_coleta()
                thread._atualizar_coleta()
                self.assertFalse(thread._coleta_ativa)
                self.assertIsNone(thread.telemetria)

    def test_captura_automatica_ocorre_na_entrada_do_alerta_uma_vez(self):
        with tempfile.TemporaryDirectory() as pasta:
            criar_telemetria = lambda: Telemetria(
                pasta=pasta, session_id="alerta", agora=10.0
            )
            thread = MonitoramentoThread()
            thread.olhos = SimpleNamespace(tempo_minimo_fechamento=1.5)
            thread.boca = SimpleNamespace(tempo_minimo_bocejo=1.0)
            thread._coleta_ativa = True

            with patch("monitoramento.Telemetria", side_effect=criar_telemetria):
                thread.telemetria = criar_telemetria()
                dados = {
                    "estado": "ATENCAO",
                    "estado_olhos": "FECHADOS",
                    "tempo_olho_fechado": 1.5,
                    "estado_boca": "FECHADA",
                    "tempo_abertura": 0.0,
                    "estado_cabeca": "NORMAL",
                }
                frame = np.zeros((20, 20, 3), dtype=np.uint8)
                thread._registrar_frame(dados, frame, 1, 10.1)
                thread._registrar_frame(dados, frame, 2, 10.2)
                thread.telemetria.fechar()

            capturas = list((Path(pasta) / "alerta" / "capturas").glob("*.png"))
            self.assertEqual(len(capturas), 1)
            self.assertTrue(capturas[0].name.startswith("automatica_"))


if __name__ == "__main__":
    unittest.main()
