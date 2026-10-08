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