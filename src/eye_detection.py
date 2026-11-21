
import math
from collections import deque
from statistics import median


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
    def __init__(
        self,
        tempo_calibracao=5,
        tempo_minimo_fechamento=1.5,
        janela_frequencia=60.0,
        fator_limiar=0.96,
        minimo_amostras_calibracao=10,
    ):
        self.tempo_calibracao = tempo_calibracao
        self.tempo_minimo_fechamento = tempo_minimo_fechamento
        self.janela_frequencia = janela_frequencia
        self.fator_limiar = fator_limiar
        self.minimo_amostras_calibracao = minimo_amostras_calibracao

        # Registro temporal para cálculo do PERCLOS
        self.amostras_perclos = deque()
        self.estado_perclos_anterior = None
        self.ultimo_tempo_perclos = None

        self.perclos = None
        self.tempo_observado_perclos = 0.0
        self.cobertura_perclos = None
        self.perclos_valido = False

        self.janela_perclos = 60.0
        self.intervalo_maximo_perclos = 0.5

        # Limite experimental de cobertura
        self.cobertura_minima_perclos = 0.75

        self.inicio = None
        self.calibrando = True
        self.valores_calibracao = []
        self.valores_calibracao_direito = []
        self.valores_calibracao_esquerdo = []

        self.ear_referencia = None
        self.limiar_ear = None
        self.ear_referencia_direito = None
        self.ear_referencia_esquerdo = None
        self.limiar_ear_direito = None
        self.limiar_ear_esquerdo = None

        self.inicio_olho_fechado = None

        # Registros dos eventos
        self.eventos = []
        self.ultimo_evento = None

    def atualizar(
        self,
        ear_medio,
        tempo_atual,
        ear_direito=None,
        ear_esquerdo=None,
    ):
        self.ultimo_evento = None

        valores = (ear_medio, ear_direito, ear_esquerdo)
        if not math.isfinite(ear_medio) or any(
            valor is not None and not math.isfinite(valor)
            for valor in valores[1:]
        ):
            return False, 0

        if self.inicio is None:
            self.inicio = tempo_atual

        # Calibração
        if self.calibrando:
            self.valores_calibracao.append(ear_medio)
            if ear_direito is not None and ear_esquerdo is not None:
                self.valores_calibracao_direito.append(ear_direito)
                self.valores_calibracao_esquerdo.append(ear_esquerdo)

            tempo_calibracao = tempo_atual - self.inicio

            if (
                tempo_calibracao >= self.tempo_calibracao
                and len(self.valores_calibracao)
                >= self.minimo_amostras_calibracao
            ):
                self.ear_referencia = median(self.valores_calibracao)
                self.limiar_ear = self.ear_referencia * self.fator_limiar

                if self.valores_calibracao_direito:
                    self.ear_referencia_direito = median(
                        self.valores_calibracao_direito
                    )
                    self.limiar_ear_direito = (
                        self.ear_referencia_direito * self.fator_limiar
                    )
                if self.valores_calibracao_esquerdo:
                    self.ear_referencia_esquerdo = median(
                        self.valores_calibracao_esquerdo
                    )
                    self.limiar_ear_esquerdo = (
                        self.ear_referencia_esquerdo * self.fator_limiar
                    )
                self.calibrando = False

            return False, 0

        # Classificação do estado dos olhos
        if (
            ear_direito is not None
            and ear_esquerdo is not None
            and self.limiar_ear_direito is not None
            and self.limiar_ear_esquerdo is not None
        ):
            olhos_fechados = (
                ear_direito < self.limiar_ear_direito
                and ear_esquerdo < self.limiar_ear_esquerdo
            )
        else:
            olhos_fechados = ear_medio < self.limiar_ear

        # Atualização do PERCLOS
        self.perclos = self.atualizar_perclos(
            olhos_fechados,
            tempo_atual
        )

        # Início ou continuidade do fechamento
        if olhos_fechados:
            if self.inicio_olho_fechado is None:
                self.inicio_olho_fechado = tempo_atual

            tempo_fechado = (
                tempo_atual - self.inicio_olho_fechado
            )

            return True, tempo_fechado

        # Os olhos abriram: finaliza o evento
        if self.inicio_olho_fechado is not None:
            inicio = self.inicio_olho_fechado
            duracao = tempo_atual - inicio

            prolongado = (
                duracao >= self.tempo_minimo_fechamento
            )

            evento = {
                "tipo": (
                    "FECHAMENTO_PROLONGADO"
                    if prolongado
                    else "PISCADA"
                ),
                "inicio": inicio,
                "fim": tempo_atual,
                "duracao": duracao,
                "prolongado": prolongado
            }

            self.eventos.append(evento)
            self.ultimo_evento = evento
            self.inicio_olho_fechado = None

            return False, 0

        return False, 0

    def atualizar_perclos(self, olhos_fechados, tempo_atual):
        # Registra o intervalo usando o estado da amostra anterior
        if self.ultimo_tempo_perclos is not None:
            intervalo = tempo_atual - self.ultimo_tempo_perclos

            if 0 < intervalo <= self.intervalo_maximo_perclos:
                self.amostras_perclos.append((
                    self.ultimo_tempo_perclos,
                    tempo_atual,
                    self.estado_perclos_anterior
                ))

        self.ultimo_tempo_perclos = tempo_atual
        self.estado_perclos_anterior = olhos_fechados

        # Remove amostras fora da janela temporal
        limite = tempo_atual - self.janela_perclos

        while (
            self.amostras_perclos
            and self.amostras_perclos[0][1] <= limite
        ):
            self.amostras_perclos.popleft()

        tempo_fechado = 0.0
        tempo_observado = 0.0

        for inicio, fim, fechado in self.amostras_perclos:
            inicio_util = max(inicio, limite)
            duracao = fim - inicio_util

            tempo_observado += duracao

            if fechado:
                tempo_fechado += duracao

        # Atualiza os dados de cobertura
        self.tempo_observado_perclos = tempo_observado

        self.cobertura_perclos = min(
            tempo_observado / self.janela_perclos,
            1.0
        )

        # Verifica se há cobertura suficiente
        self.perclos_valido = (
            tempo_observado > 0
            and self.cobertura_perclos >= self.cobertura_minima_perclos
        )

        if tempo_observado == 0:
            return None

        return tempo_fechado / tempo_observado

    def frequencia_fechamentos(self, tempo_atual):
        limite = tempo_atual - self.janela_frequencia

        return sum(
            1 for evento in self.eventos
            if evento["fim"] >= limite
        )

    def frequencia_fechamentos_prolongados(self, tempo_atual):
        limite = tempo_atual - self.janela_frequencia

        return sum(
            1 for evento in self.eventos
            if evento["prolongado"]
            and evento["fim"] >= limite
        )

    def interromper(self, tempo_atual):
        """Interrompe um fechamento quando o rosto desaparece."""

        # Impede a contabilização de intervalos sem observação
        self.ultimo_tempo_perclos = None
        self.estado_perclos_anterior = None
        self.amostras_perclos.clear()
        self.perclos = None
        self.tempo_observado_perclos = 0.0
        self.cobertura_perclos = 0.0

        # Invalida o PERCLOS durante a ausência do rosto
        self.perclos_valido = False
        self.ultimo_evento = None

        if self.inicio_olho_fechado is None:
            return

        evento = {
            "tipo": "FECHAMENTO_INTERROMPIDO",
            "inicio": self.inicio_olho_fechado,
            "fim": tempo_atual,
            "duracao": tempo_atual - self.inicio_olho_fechado,
            "prolongado": False,
            "motivo": "SEM_ROSTO"
        }

        self.eventos.append(evento)
        self.ultimo_evento = evento
        self.inicio_olho_fechado = None
