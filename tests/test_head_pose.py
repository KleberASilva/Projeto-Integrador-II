import unittest
from types import SimpleNamespace

import cv2
import numpy as np

from src.head_pose import (
    FiltroOrientacao,
    MODELO_ROSTO_3D,
    PONTOS_ROSTO,
    estimar_orientacao,
)


def landmarks_projetados(eixo, graus, largura=640, altura=480):
    camera = np.array(
        [[largura, 0, largura / 2], [0, largura, altura / 2], [0, 0, 1]],
        dtype=float,
    )
    vetor_rotacao = np.zeros((3, 1), dtype=float)
    vetor_rotacao[eixo, 0] = np.deg2rad(graus)
    pontos, _ = cv2.projectPoints(
        MODELO_ROSTO_3D,
        vetor_rotacao,
        np.array([[0.0], [0.0], [1000.0]]),
        camera,
        np.zeros((4, 1), dtype=float),
    )
    landmarks = [SimpleNamespace(x=0.0, y=0.0) for _ in range(468)]
    for indice, (x, y) in zip(PONTOS_ROSTO, pontos.reshape(-1, 2)):
        landmarks[indice] = SimpleNamespace(
            x=float(x / largura), y=float(y / altura)
        )
    return landmarks


class HeadPoseTests(unittest.TestCase):
    def test_estimativa_preserva_pitch_yaw_e_roll(self):
        for eixo, esperado in ((0, 20.0), (1, 30.0), (2, -25.0)):
            orientacao = estimar_orientacao(
                landmarks_projetados(eixo, esperado), 640, 480
            )
            self.assertIsNotNone(orientacao)
            yaw, pitch, roll = orientacao
            valores = (pitch, yaw, roll)
            self.assertAlmostEqual(valores[eixo], esperado, delta=0.5)

    def test_yaw_tem_magnitude_simetrica_nos_dois_sentidos(self):
        esquerda = estimar_orientacao(
            landmarks_projetados(1, -35.0), 640, 480
        )[0]
        direita = estimar_orientacao(
            landmarks_projetados(1, 35.0), 640, 480
        )[0]
        self.assertAlmostEqual(abs(esquerda), abs(direita), delta=0.5)
        self.assertAlmostEqual(esquerda, -direita, delta=0.5)

    def test_calibracao_da_cabeca_aceita_tempo_monotono_injetado(self):
        filtro = FiltroOrientacao()
        filtro.duracao_calibracao = 1.0
        self.assertIsNone(filtro.calibrar((10.0, 2.0, -1.0), tempo_atual=0.0))
        relativo = filtro.calibrar((10.0, 2.0, -1.0), tempo_atual=1.0)
        self.assertIsNotNone(relativo)
        self.assertAlmostEqual(relativo[0], 0.0)
        self.assertAlmostEqual(relativo[1], 0.0)
        self.assertAlmostEqual(relativo[2], 0.0)


if __name__ == "__main__":
    unittest.main()
