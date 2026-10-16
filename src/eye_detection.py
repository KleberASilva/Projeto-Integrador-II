import math


OLHO_DIREITO = [33, 159, 145, 133, 153, 160]
OLHO_ESQUERDO = [362, 386, 380, 263, 374, 385]


def distancia(p1, p2):
    return math.sqrt(
        (p1.x - p2.x) ** 2 +
        (p1.y - p2.y) ** 2
    )


def calcular_ear(landmarks, pontos):
    p1 = landmarks[pontos[0]]
    p2 = landmarks[pontos[1]]
    p3 = landmarks[pontos[2]]
    p4 = landmarks[pontos[3]]
    p5 = landmarks[pontos[4]]
    p6 = landmarks[pontos[5]]

    distancia_vertical_1 = distancia(p2, p6)
    distancia_vertical_2 = distancia(p3, p5)
    distancia_horizontal = distancia(p1, p4)

    return (
        distancia_vertical_1 +
        distancia_vertical_2
    ) / (2 * distancia_horizontal)


def detectar_olhos(landmarks):
    ear_direito = calcular_ear(
        landmarks,
        OLHO_DIREITO
    )

    ear_esquerdo = calcular_ear(
        landmarks,
        OLHO_ESQUERDO
    )

    ear_medio = (
        ear_direito +
        ear_esquerdo
    ) / 2

    return ear_direito, ear_esquerdo, ear_medio

class DetectorOlhos:
    def __init__(self, tempo_calibracao=5):
        self.tempo_calibracao = tempo_calibracao

        self.inicio = None
        self.calibrando = True

        self.valores_calibracao = []

        self.ear_referencia = None
        self.limiar_ear = None

        self.inicio_olho_fechado = None

    def atualizar(self, ear_medio, tempo_atual):
        # Inicia a calibração
        if self.inicio is None:
            self.inicio = tempo_atual

        # -------------------------
        # CALIBRAÇÃO
        # -------------------------
        if self.calibrando:

            self.valores_calibracao.append(ear_medio)

            tempo_calibracao = tempo_atual - self.inicio

            if tempo_calibracao >= self.tempo_calibracao:

                self.ear_referencia = sum(
                    self.valores_calibracao
                ) / len(self.valores_calibracao)

                self.limiar_ear = self.ear_referencia * 0.96

                self.calibrando = False

            return False, 0

        # -------------------------
        # DETECÇÃO
        # -------------------------

        if ear_medio < self.limiar_ear:

            if self.inicio_olho_fechado is None:
                self.inicio_olho_fechado = tempo_atual

            tempo_olho_fechado = (
                tempo_atual - self.inicio_olho_fechado
            )

            olhos_fechados = True

        else:

            self.inicio_olho_fechado = None
            tempo_olho_fechado = 0
            olhos_fechados = False

        return olhos_fechados, tempo_olho_fechado