
import math
from statistics import median

# Pontos da boca no MediaPipe (cantos e lábios superior/inferior)
BOCA = [61, 37, 267, 291, 314, 84]


def distancia(p1, p2):
    return math.hypot(p1.x - p2.x, p1.y - p2.y)


def calcular_mar(landmarks, pontos):
    p_esq, p_dir = landmarks[pontos[0]], landmarks[pontos[3]]
    distancia_horizontal = distancia(p_esq, p_dir)

    if distancia_horizontal == 0:
        return 0.0

    pares_verticais = [
        (landmarks[pontos[1]], landmarks[pontos[5]]),
        (landmarks[pontos[2]], landmarks[pontos[4]])
    ]

    soma_vertical = sum(
        distancia(p_cima, p_baixo)
        for p_cima, p_baixo in pares_verticais
    )

    return soma_vertical / (2 * distancia_horizontal)


class DetectorBocejo:
    def __init__(
        self,
        tempo_calibracao=5,
        tempo_minimo_bocejo=1.0,
        janela_frequencia=60.0,
        fator_limiar=1.5,
        minimo_amostras_calibracao=10,
    ):
        self.tempo_calibracao = tempo_calibracao
        self.tempo_minimo_bocejo = tempo_minimo_bocejo
        self.janela_frequencia = janela_frequencia
        self.fator_limiar = fator_limiar
        self.minimo_amostras_calibracao = minimo_amostras_calibracao

        self.inicio = None
        self.calibrando = True
        self.valores_calibracao = []
        self.mar_referencia = None
        self.limiar_mar = None

        self.inicio_bocejo = None
        self.eventos = []
        self.ultimo_evento = None

    def atualizar(self, mar_atual, tempo_atual):
        self.ultimo_evento = None

        if self.inicio is None:
            self.inicio = tempo_atual

        if self.calibrando:
            self.valores_calibracao.append(mar_atual)

            if (
                (tempo_atual - self.inicio) >= self.tempo_calibracao
                and len(self.valores_calibracao)
                >= self.minimo_amostras_calibracao
            ):
                self.mar_referencia = median(self.valores_calibracao)
                self.limiar_mar = self.mar_referencia * self.fator_limiar
                self.calibrando = False

            return False, 0

        if mar_atual > self.limiar_mar:
            if self.inicio_bocejo is None:
                self.inicio_bocejo = tempo_atual

            tempo_aberto = tempo_atual - self.inicio_bocejo
            return False, tempo_aberto

        if self.inicio_bocejo is not None:
            inicio = self.inicio_bocejo
            duracao = tempo_atual - inicio
            confirmado = duracao >= self.tempo_minimo_bocejo

            evento = {
                "tipo": "BOCEJO" if confirmado else "ABERTURA_CURTA",
                "inicio": inicio,
                "fim": tempo_atual,
                "duracao": duracao,
                "confirmado": confirmado
            }

            self.eventos.append(evento)
            self.ultimo_evento = evento
            self.inicio_bocejo = None

            return confirmado, 0

        return False, 0

    def frequencia_bocejos(self, tempo_atual):
        limite = tempo_atual - self.janela_frequencia

        return sum(
            1 for evento in self.eventos
            if evento["confirmado"] and evento["fim"] >= limite
        )

    def interromper(self, tempo_atual):
        self.ultimo_evento = None
        if self.inicio_bocejo is None:
            return

        evento = {
            "tipo": "ABERTURA_INTERROMPIDA",
            "inicio": self.inicio_bocejo,
            "fim": tempo_atual,
            "duracao": tempo_atual - self.inicio_bocejo,
            "confirmado": False,
            "motivo": "SEM_ROSTO"
        }

        self.eventos.append(evento)
        self.ultimo_evento = evento
        self.inicio_bocejo = None
