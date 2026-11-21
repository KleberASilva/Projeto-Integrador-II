import unittest

from src.boca import DetectorBocejo
from src.eye_detection import DetectorOlhos


class DetectorTests(unittest.TestCase):
    def _calibrar_olhos(self):
        detector = DetectorOlhos(
            tempo_calibracao=1.0,
            tempo_minimo_fechamento=1.5,
        )
        for indice in range(11):
            tempo = indice * 0.1
            detector.atualizar(
                0.30,
                tempo,
                ear_direito=0.30,
                ear_esquerdo=0.30,
            )
        return detector

    def test_calibracao_dos_olhos_usa_referencias_individuais(self):
        detector = self._calibrar_olhos()
        self.assertFalse(detector.calibrando)
        self.assertAlmostEqual(detector.ear_referencia, 0.30)
        self.assertAlmostEqual(detector.ear_referencia_direito, 0.30)
        self.assertAlmostEqual(detector.ear_referencia_esquerdo, 0.30)
        self.assertAlmostEqual(detector.limiar_ear, 0.30)

    def test_fechamento_considera_media_quando_um_olho_tem_landmark_ruim(self):
        detector = self._calibrar_olhos()
        fechado, _ = detector.atualizar(
            0.20, 2.0, ear_direito=0.10, ear_esquerdo=0.30
        )
        self.assertTrue(fechado)

    def test_piscada_normal_nao_e_fechamento_prolongado(self):
        detector = self._calibrar_olhos()
        fechado, duracao = detector.atualizar(
            0.1, 2.0, ear_direito=0.1, ear_esquerdo=0.1
        )
        self.assertTrue(fechado)
        self.assertEqual(duracao, 0.0)

        fechado, duracao = detector.atualizar(
            0.1, 2.2, ear_direito=0.1, ear_esquerdo=0.1
        )
        self.assertTrue(fechado)
        self.assertAlmostEqual(duracao, 0.2)

        fechado, duracao = detector.atualizar(
            0.3, 2.3, ear_direito=0.3, ear_esquerdo=0.3
        )
        self.assertFalse(fechado)
        self.assertEqual(duracao, 0)
        self.assertEqual(detector.ultimo_evento["tipo"], "PISCADA")
        self.assertFalse(detector.ultimo_evento["prolongado"])

    def test_fechamento_prolongado_e_interrupcao_por_ausencia(self):
        detector = self._calibrar_olhos()
        detector.atualizar(0.1, 2.0, ear_direito=0.1, ear_esquerdo=0.1)
        detector.atualizar(0.1, 3.6, ear_direito=0.1, ear_esquerdo=0.1)
        detector.atualizar(0.3, 3.7, ear_direito=0.3, ear_esquerdo=0.3)
        self.assertEqual(
            detector.ultimo_evento["tipo"], "FECHAMENTO_PROLONGADO"
        )
        self.assertTrue(detector.ultimo_evento["prolongado"])

        detector.atualizar(0.1, 4.0, ear_direito=0.1, ear_esquerdo=0.1)
        detector.interromper(4.4)
        self.assertEqual(
            detector.ultimo_evento["tipo"], "FECHAMENTO_INTERROMPIDO"
        )
        self.assertEqual(detector.ultimo_evento["motivo"], "SEM_ROSTO")
        detector.interromper(4.5)
        self.assertIsNone(detector.ultimo_evento)

    def test_interrupcao_reinicia_janela_do_perclos(self):
        detector = self._calibrar_olhos()
        detector.atualizar(0.3, 2.0, ear_direito=0.3, ear_esquerdo=0.3)
        detector.atualizar(0.1, 2.2, ear_direito=0.1, ear_esquerdo=0.1)
        self.assertGreater(detector.tempo_observado_perclos, 0.0)

        detector.interromper(3.0)

        self.assertIsNone(detector.perclos)
        self.assertEqual(detector.tempo_observado_perclos, 0.0)
        self.assertEqual(detector.cobertura_perclos, 0.0)
        self.assertFalse(detector.perclos_valido)

    def test_calibracao_da_boca_e_robusta_a_uma_abertura_isolada(self):
        detector = DetectorBocejo(
            tempo_calibracao=1.0,
            tempo_minimo_bocejo=1.0,
        )
        valores = (
            0.20, 0.20, 1.0, 0.20, 0.20, 0.20,
            0.20, 0.20, 0.20, 0.20, 0.20,
        )
        for indice, valor in enumerate(valores):
            detector.atualizar(valor, indice * 0.2)

        self.assertFalse(detector.calibrando)
        self.assertAlmostEqual(detector.mar_referencia, 0.20)
        self.assertAlmostEqual(detector.limiar_mar, 0.30)

        confirmado, duracao = detector.atualizar(0.5, 2.0)
        self.assertFalse(confirmado)
        self.assertEqual(duracao, 0.0)
        confirmado, duracao = detector.atualizar(0.5, 3.2)
        self.assertFalse(confirmado)
        self.assertAlmostEqual(duracao, 1.2)
        confirmado, duracao = detector.atualizar(0.2, 3.3)
        self.assertTrue(confirmado)
        self.assertEqual(duracao, 0)
        self.assertTrue(detector.ultimo_evento["confirmado"])


if __name__ == "__main__":
    unittest.main()
