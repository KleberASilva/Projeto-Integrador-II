
import cv2
import numpy as np
import math
import time

PONTOS_ROSTO = [1, 152, 33, 263, 61, 291]

MODELO_ROSTO_3D = np.array([
    (0.0, 0.0, 0.0),
    (0.0, -330.0, -65.0),
    (-225.0, 170.0, -135.0),
    (225.0, 170.0, -135.0),
    (-150.0, -150.0, -125.0),
    (150.0, -150.0, -125.0)
], dtype=np.float64)

def estimar_orientacao(landmarks, largura, altura):
    pontos_2d = np.array([
        (
            landmarks[indice].x * largura,
            landmarks[indice].y * altura
        )
        for indice in PONTOS_ROSTO
    ], dtype=np.float64)

    focal = largura
    centro = (largura / 2, altura / 2)

    matriz_camera = np.array([
        [focal, 0, centro[0]],
        [0, focal, centro[1]],
        [0, 0, 1]
    ], dtype=np.float64)

    distorcao = np.zeros((4, 1), dtype=np.float64)

    sucesso, vetor_rotacao, _ = cv2.solvePnP(
        MODELO_ROSTO_3D,
        pontos_2d,
        matriz_camera,
        distorcao,
        flags=cv2.SOLVEPNP_ITERATIVE
    )

    if not sucesso:
        return None

    matriz_rotacao, _ = cv2.Rodrigues(vetor_rotacao)
    angulos = cv2.RQDecomp3x3(matriz_rotacao)[0]

    pitch, yaw, _ = angulos

    pitch = (pitch + 360) % 360
    pitch = (pitch - 180 + 180) % 360 - 180

    olho_direito = landmarks[33]
    olho_esquerdo = landmarks[263]

    dx = (olho_esquerdo.x - olho_direito.x) * largura
    dy = (olho_esquerdo.y - olho_direito.y) * altura

    roll = math.degrees(math.atan2(dy, dx))

    return yaw, pitch, roll


class FiltroOrientacao:
    def __init__(self):
        self.anterior = None
        self.suspeita = None
        
        self.referencia = None
        self.amostras_calibracao = []
        self.inicio_calibracao = None
        self.duracao_calibracao = 3.0

        # Limites de variação para Yaw, Pitch e Roll
        self.limites = np.array([20.0, 15.0, 15.0])

    def calibrar(self, orientacao):
        if orientacao is None:
            return None
        
        if self.referencia is not None:
            return tuple(np.array(orientacao) - self.referencia)
    
        if self.inicio_calibracao is None:
            self.inicio_calibracao = time.monotonic()

        self.amostras_calibracao.append(orientacao)

        tempo_decorrido = time.monotonic() - self.inicio_calibracao

        if tempo_decorrido < self.duracao_calibracao:
            return None

        # Média das orientações coletadas
        self.referencia = np.mean(
            self.amostras_calibracao,
            axis=0
        )

        print(f"Calibração concluída! Referência: {self.referencia}")

        return tuple(np.array(orientacao) - self.referencia)

    def atualizar(self, orientacao):
        if orientacao is None:
            return None if self.anterior is None else tuple(self.anterior)

        atual = np.array(orientacao, dtype=float)

        if not np.all(np.isfinite(atual)):
            return None if self.anterior is None else tuple(self.anterior)

        # Primeira leitura válida
        if self.anterior is None:
            self.anterior = atual
            return tuple(atual)

        diferenca = np.abs(atual - self.anterior)

        # Movimento dentro dos limites: aceita normalmente
        if np.all(diferenca <= self.limites):
            self.anterior = atual
            self.suspeita = None
            return tuple(atual)

        # Primeiro salto inesperado: aguarda confirmação
        if self.suspeita is None:
            self.suspeita = atual
            return tuple(self.anterior)

        # Verifica se a nova leitura confirma a suspeita
        diferenca_suspeita = np.abs(atual - self.suspeita)

        if np.all(diferenca_suspeita <= self.limites):
            self.anterior = atual
            self.suspeita = None
            return tuple(atual)

        # Descarta a suspeita anterior e guarda a nova
        self.suspeita = atual

        return tuple(self.anterior)