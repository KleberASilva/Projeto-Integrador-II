
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


def diferenca_angular(atual, anterior):
    return (atual - anterior + 180) % 360 - 180


def normalizar_angulo(angulo):
    """Retorna um ângulo no intervalo [-180, 180)."""
    return (float(angulo) + 180.0) % 360.0 - 180.0


def media_angular(amostras):
    radianos = np.radians(amostras)

    seno = np.mean(np.sin(radianos), axis=0)
    cosseno = np.mean(np.cos(radianos), axis=0)

    return np.degrees(np.arctan2(seno, cosseno))


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

    pitch = normalizar_angulo(pitch)
    yaw = normalizar_angulo(yaw)

    olho_direito = landmarks[33]
    olho_esquerdo = landmarks[263]

    dx = (olho_esquerdo.x - olho_direito.x) * largura
    dy = (olho_esquerdo.y - olho_direito.y) * altura

    roll = math.degrees(math.atan2(dy, dx))

    return yaw, pitch, normalizar_angulo(roll)


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

    def calibrar(self, orientacao, tempo_atual=None):
        if orientacao is None:
            return None

        if self.referencia is not None:
            diferenca = diferenca_angular(
                np.array(orientacao),
                self.referencia
            )
            return tuple(diferenca)

        if self.inicio_calibracao is None:
            self.inicio_calibracao = (
                time.monotonic() if tempo_atual is None else tempo_atual
            )

        self.amostras_calibracao.append(orientacao)

        agora = time.monotonic() if tempo_atual is None else tempo_atual
        tempo_decorrido = agora - self.inicio_calibracao

        if tempo_decorrido < self.duracao_calibracao:
            return None

        # Calcula a referência usando média circular
        self.referencia = media_angular(
            self.amostras_calibracao
        )

        print(
            f"Calibração concluída! "
            f"Referência: {self.referencia}"
        )

        diferenca = diferenca_angular(
            np.array(orientacao),
            self.referencia
        )

        return tuple(diferenca)

    def atualizar(self, orientacao):
        if orientacao is None:
            return (
                None
                if self.anterior is None
                else tuple(self.anterior)
            )

        atual = np.array(orientacao, dtype=float)

        if not np.all(np.isfinite(atual)):
            return (
                None
                if self.anterior is None
                else tuple(self.anterior)
            )

        # Primeira leitura válida
        if self.anterior is None:
            self.anterior = atual
            return tuple(atual)

        diferenca = np.abs(
            diferenca_angular(atual, self.anterior)
        )

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
        diferenca_suspeita = np.abs(
            diferenca_angular(atual, self.suspeita)
        )

        if np.all(diferenca_suspeita <= self.limites):
            self.anterior = atual
            self.suspeita = None
            return tuple(atual)

        # Descarta a suspeita anterior e guarda a nova
        self.suspeita = atual

        return tuple(self.anterior)


class DetectorCabeca:
    def __init__(
        self,
        limite_pitch=15.0,
        limite_yaw=50.0,
        tempo_minimo=1.5,
        janela_frequencia=60.0
    ):
        self.limite_pitch = limite_pitch
        self.limite_yaw = limite_yaw
        self.tempo_minimo = tempo_minimo
        self.janela_frequencia = janela_frequencia

        self.inicio_evento = None
        self.tipo_evento = None

        self.eventos = []
        self.ultimo_evento = None

    def atualizar(self, yaw, pitch, tempo_atual):
        self.ultimo_evento = None

        if yaw is None or pitch is None:
            return False, 0

        desvio_yaw = abs(yaw) > self.limite_yaw
        desvio_pitch = abs(pitch) > self.limite_pitch

        # Identifica o tipo de movimento
        if desvio_yaw and desvio_pitch:
            tipo = "MOVIMENTO_COMBINADO"
        elif desvio_yaw:
            tipo = "ROTACAO"
        elif desvio_pitch:
            tipo = "INCLINACAO"
        else:
            tipo = None

        # Início ou continuidade do evento
        if tipo is not None:
            if self.inicio_evento is None:
                self.inicio_evento = tempo_atual
                self.tipo_evento = tipo

            else:
                if tipo == "MOVIMENTO_COMBINADO":
                    self.tipo_evento = tipo

            duracao = tempo_atual - self.inicio_evento

            return duracao >= self.tempo_minimo, duracao

        # Retorno à faixa normal: finaliza o evento
        if self.inicio_evento is not None:
            inicio = self.inicio_evento
            duracao = tempo_atual - inicio

            confirmado = duracao >= self.tempo_minimo

            evento = {
                "tipo": self.tipo_evento,
                "inicio": inicio,
                "fim": tempo_atual,
                "duracao": duracao,
                "confirmado": confirmado
            }

            self.eventos.append(evento)
            self.ultimo_evento = evento

            self.inicio_evento = None
            self.tipo_evento = None

            return False, 0

        return False, 0

    def frequencia_movimentos(self, tempo_atual):
        limite = tempo_atual - self.janela_frequencia

        return sum(
            1 for evento in self.eventos
            if evento["confirmado"]
            and evento["fim"] >= limite
        )

    def interromper(self, tempo_atual):
        """Interrompe o evento quando o rosto desaparece."""
        if self.inicio_evento is None:
            return

        evento = {
            "tipo": self.tipo_evento,
            "inicio": self.inicio_evento,
            "fim": tempo_atual,
            "duracao": tempo_atual - self.inicio_evento,
            "confirmado": tempo_atual - self.inicio_evento >= self.tempo_minimo,
            "motivo": "SEM_ROSTO"
        }

        self.eventos.append(evento)
        self.ultimo_evento = evento

        self.inicio_evento = None
        self.tipo_evento = None
