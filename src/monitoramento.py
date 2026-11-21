
import os
import time

import cv2
import mediapipe as mp

from PySide6.QtCore import QThread, Signal

from eye_detection import detectar_olhos, DetectorOlhos
from boca import BOCA, calcular_mar, DetectorBocejo
from head_pose import estimar_orientacao, FiltroOrientacao, DetectorCabeca
from classificador_fadiga import ClassificadorFadiga
from telemetria import Telemetria


MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "models",
    "face_landmarker.task"
)


class MonitoramentoThread(QThread):
    frame_pronto = Signal(object)
    resultado_pronto = Signal(object)
    sem_camera = Signal()
    captura_pronta = Signal(str)
    coleta_alterada = Signal(bool)

    def __init__(self):
        super().__init__()
        self._executando = True
        self._recalibrar = False
        self.telemetria = None
        self._frame_atual = 0
        self._marcacoes_pendentes = []
        self._captura_solicitada = False
        self._coleta_ativa = False
        self._solicitar_inicio_coleta = False
        self._solicitar_fim_coleta = False
        self._sinais_automaticos_ativos = {}

    def parar(self):
        self._executando = False
        self.wait()

    def solicitar_recalibracao(self):
        self._recalibrar = True

    def iniciar_coleta(self):
        self._solicitar_inicio_coleta = True
        self._solicitar_fim_coleta = False

    def parar_coleta(self):
        self._solicitar_fim_coleta = True
        self._solicitar_inicio_coleta = False
        self._captura_solicitada = False

    def _atualizar_coleta(self):
        if self._solicitar_fim_coleta:
            self._solicitar_fim_coleta = False
            if self.telemetria is not None:
                self.telemetria.fechar()
                self.telemetria = None
            if self._coleta_ativa:
                self._coleta_ativa = False
                self.coleta_alterada.emit(False)

        if self._solicitar_inicio_coleta and not self._coleta_ativa:
            self._solicitar_inicio_coleta = False
            self.telemetria = Telemetria()
            self._coleta_ativa = True
            self._sinais_automaticos_ativos = {}
            self.coleta_alterada.emit(True)

    def solicitar_captura(self):
        """Solicita uma captura no prÃ³ximo frame processado."""
        if not self._coleta_ativa:
            return False
        self._captura_solicitada = True
        return True

    def _adicionar_diagnostico(self, dados):
        parametros = self.classificador.parametros
        diagnostico = self.classificador.diagnostico or {}
        dados.update({
            "escore_olhos": self.classificador.escores["olhos"],
            "escore_boca": self.classificador.escores["boca"],
            "escore_cabeca": self.classificador.escores["cabeca"],
            "peso_olhos": parametros.peso_olhos,
            "peso_boca": parametros.peso_boca,
            "peso_cabeca": parametros.peso_cabeca,
            "escore_total": self.classificador.escore_total,
            "categorias_significativas": self.classificador.categorias_significativas,
            "motivo_classificacao": diagnostico.get("motivo_classificacao"),
            "sinal_atencao": diagnostico.get("sinal_atencao"),
            "sinal_fadiga": diagnostico.get("sinal_fadiga"),
            "fadiga_persistente": diagnostico.get("fadiga_persistente"),
            "persistencia_fadiga_decorrida": diagnostico.get("persistencia_fadiga_decorrida"),
            "persistencia_fadiga_necessaria": diagnostico.get("persistencia_fadiga_necessaria"),
            "persistencia_transicao_decorrida": diagnostico.get("persistencia_transicao_decorrida"),
            "persistencia_transicao_necessaria": diagnostico.get("persistencia_transicao_necessaria"),
            "candidato_transicao": diagnostico.get("candidato_transicao"),
        })
        return dados

    def _captura_automatica(self, dados):
        sinais = {
            "fechamento_prolongado": (
                dados.get("estado_olhos") == "FECHADOS"
                and (dados.get("tempo_olho_fechado") or 0.0)
                >= self.olhos.tempo_minimo_fechamento
            ),
            "abertura_prolongada": (
                dados.get("estado_boca") == "ABERTA"
                and (dados.get("tempo_abertura") or 0.0)
                >= self.boca.tempo_minimo_bocejo
            ),
            "movimento_cabeca": dados.get("estado_cabeca") == "MOVIMENTO",
            "entrada_atencao": dados.get("estado") == "ATENCAO",
            "entrada_fadiga": dados.get("estado") == "FADIGA",
        }
        novos = [
            nome for nome, ativo in sinais.items()
            if ativo and not self._sinais_automaticos_ativos.get(nome, False)
        ]
        self._sinais_automaticos_ativos = sinais
        return bool(novos), ",".join(novos)

    def _registrar_frame(self, dados, frame, numero_frame, agora):
        if not self._coleta_ativa or self.telemetria is None:
            return
        captura_automatica, motivo = self._captura_automatica(dados)
        captura_manual = self._captura_solicitada
        captura = captura_automatica or captura_manual
        self._captura_solicitada = False
        caminho = self.telemetria.registrar(
            dados,
            frame=numero_frame,
            agora=agora,
            imagem=frame.copy() if captura else None,
            captura_tipo=("manual" if captura_manual else "automatica") if captura else None,
            captura_motivo=("solicitacao_manual" if captura_manual else motivo) if captura else None,
        )
        if caminho:
            self.captura_pronta.emit(caminho)

    def registrar_marcacao(self, tipo, descricao):
        """Registra uma marcação manual na sessão sem alterar o classificador."""
        telemetria = self.telemetria
        if not self._coleta_ativa or telemetria is None:
            return False
        return telemetria.registrar_marcacao(
            tipo,
            descricao,
            frame=self._frame_atual or None,
            agora=time.monotonic(),
        )

    def _criar_detectores(self):
        self.olhos = DetectorOlhos(tempo_calibracao=5)
        self.boca = DetectorBocejo(tempo_calibracao=5)
        self.cabeca = FiltroOrientacao()
        self.detector_cabeca = DetectorCabeca()
        self.classificador = ClassificadorFadiga()

    def run(self):
        self._criar_detectores()

        camera = cv2.VideoCapture(0)

        if not camera.isOpened():
            self.sem_camera.emit()
            camera.release()
            return

        numero_frame = 0
        self._frame_atual = 0

        try:
            options = mp.tasks.vision.FaceLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(
                    model_asset_path=MODEL_PATH
                ),
                running_mode=mp.tasks.vision.RunningMode.IMAGE,
                num_faces=1
            )

            with mp.tasks.vision.FaceLandmarker.create_from_options(
                options
            ) as landmarker:

                while self._executando:

                    self._atualizar_coleta()

                    if self._recalibrar:
                        self._criar_detectores()
                        self._recalibrar = False

                    ok, frame = camera.read()

                    if not ok:
                        continue

                    frame = cv2.flip(frame, 1)
                    numero_frame += 1
                    self._frame_atual = numero_frame
                    altura, largura = frame.shape[:2]

                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    imagem = mp.Image(
                        image_format=mp.ImageFormat.SRGB,
                        data=rgb
                    )

                    resultado = landmarker.detect(imagem)

                    self.frame_pronto.emit(frame.copy())

                    agora = time.monotonic()

                    # Ausência de rosto
                    if not resultado.face_landmarks:

                        self.olhos.interromper(agora)
                        self.boca.interromper(agora)
                        self.detector_cabeca.interromper(agora)

                        dados = {
                            "estado": "SEM_ROSTO",
                            "ear": None,
                            "mar": None,
                            "pitch": None,
                            "yaw": None,
                            "roll": None,
                            "pitch_original": None,
                            "yaw_original": None,
                            "roll_original": None,
                            "pitch_filtrado": None,
                            "yaw_filtrado": None,
                            "roll_filtrado": None,
                            "pitch_relativo": None,
                            "yaw_relativo": None,
                            "roll_relativo": None,
                            "calibracao_olhos": (
                                "PRONTO" if not self.olhos.calibrando
                                else "CALIBRANDO"
                            ),
                            "calibracao_boca": (
                                "PRONTO" if not self.boca.calibrando
                                else "CALIBRANDO"
                            ),
                            "calibracao_cabeca": (
                                "PRONTO" if self.cabeca.referencia is not None
                                else "CALIBRANDO"
                            ),
                            "evento_olhos": self.olhos.ultimo_evento,
                            "evento_boca": self.boca.ultimo_evento,
                            "evento_cabeca": self.detector_cabeca.ultimo_evento,
                            "estado_olhos": "SEM_ROSTO",
                            "estado_boca": "SEM_ROSTO",
                            "estado_cabeca": "SEM_ROSTO",
                            "perclos": None,
                            "perclos_valido": False,
                            "cobertura_perclos": 0.0,
                        }

                        self._adicionar_diagnostico(dados)
                        self._registrar_frame(dados, frame, numero_frame, agora)
                        self.resultado_pronto.emit(dados)

                        continue

                    landmarks = resultado.face_landmarks[0]

                    # Olhos
                    ear_direito, ear_esquerdo, ear = detectar_olhos(
                        landmarks
                    )

                    olhos_fechados, tempo_fechado = (
                        self.olhos.atualizar(
                            ear,
                            agora,
                            ear_direito=ear_direito,
                            ear_esquerdo=ear_esquerdo,
                        )
                    )

                    # Boca
                    mar = calcular_mar(landmarks, BOCA)

                    bocejo, tempo_abertura = (
                        self.boca.atualizar(mar, agora)
                    )

                    # Cabeça
                    orientacao = estimar_orientacao(
                        landmarks, largura, altura
                    )
                    orientacao_filtrada = self.cabeca.atualizar(
                        orientacao
                    )

                    orientacao_relativa = self.cabeca.calibrar(
                        orientacao_filtrada,
                        tempo_atual=agora,
                    )

                    calibrando = (
                        self.olhos.calibrando
                        or self.boca.calibrando
                        or orientacao_relativa is None
                    )

                    pitch = None
                    yaw = None
                    roll = None

                    if orientacao_relativa is not None:
                        yaw, pitch, roll = orientacao_relativa

                    yaw_original = pitch_original = roll_original = None
                    if orientacao is not None:
                        yaw_original, pitch_original, roll_original = orientacao
                    yaw_filtrado = pitch_filtrado = roll_filtrado = None
                    if orientacao_filtrada is not None:
                        yaw_filtrado, pitch_filtrado, roll_filtrado = (
                            orientacao_filtrada
                        )

                    # Detecção de movimentos da cabeça
                    movimento_cabeca, tempo_movimento = (
                        self.detector_cabeca.atualizar(
                            yaw,
                            pitch,
                            agora
                        )
                    )

                    # Classificação
                    estado = self.classificador.atualizar(
                        {
                            "estado": (
                                "CALIBRANDO" if calibrando else "ATENTO"
                            ),
                            "olhos_fechados": olhos_fechados,
                            "perclos": self.olhos.perclos,
                            "perclos_valido": self.olhos.perclos_valido,
                            "perclos_cobertura": self.olhos.cobertura_perclos,
                            "tempo_olho_fechado": tempo_fechado,
                            "eventos": {
                                "olhos": self.olhos.ultimo_evento,
                                "boca": self.boca.ultimo_evento,
                                "cabeca": self.detector_cabeca.ultimo_evento,
                            },
                            "frequencia_fechamentos_prolongados": (
                                self.olhos.frequencia_fechamentos_prolongados(
                                    agora
                                )
                            ),
                            "frequencia_bocejos": (
                                self.boca.frequencia_bocejos(agora)
                            ),
                            "frequencia_movimentos": (
                                self.detector_cabeca.frequencia_movimentos(
                                    agora
                                )
                            ),
                            "bocejo": bocejo,
                            "movimento_cabeca": movimento_cabeca,
                        },
                        agora,
                    )

                    # Organização dos dados
                    dados = {
                        # Estado atual
                        "estado": estado,

                        # Medidas
                        "ear": ear,
                        "mar": mar,
                        "pitch": pitch,
                        "yaw": yaw,
                        "roll": roll,
                        "pitch_original": pitch_original,
                        "yaw_original": yaw_original,
                        "roll_original": roll_original,
                        "pitch_filtrado": pitch_filtrado,
                        "yaw_filtrado": yaw_filtrado,
                        "roll_filtrado": roll_filtrado,
                        "pitch_relativo": pitch,
                        "yaw_relativo": yaw,
                        "roll_relativo": roll,
                        "calibracao_olhos": (
                            "PRONTO" if not self.olhos.calibrando
                            else "CALIBRANDO"
                        ),
                        "calibracao_boca": (
                            "PRONTO" if not self.boca.calibrando
                            else "CALIBRANDO"
                        ),
                        "calibracao_cabeca": (
                            "PRONTO" if self.cabeca.referencia is not None
                            else "CALIBRANDO"
                        ),

                        # Limiares
                        "limiar_ear": self.olhos.limiar_ear,
                        "limiar_ear_direito": self.olhos.limiar_ear_direito,
                        "limiar_ear_esquerdo": self.olhos.limiar_ear_esquerdo,
                        "ear_referencia": self.olhos.ear_referencia,
                        "ear_referencia_direito": self.olhos.ear_referencia_direito,
                        "ear_referencia_esquerdo": self.olhos.ear_referencia_esquerdo,
                        "limiar_mar": self.boca.limiar_mar,
                        "mar_referencia": self.boca.mar_referencia,
                        "limiar_pitch": self.detector_cabeca.limite_pitch,
                        "limiar_yaw": self.detector_cabeca.limite_yaw,
                        "limiar_roll": None,

                        # Olhos
                        "ear_direito": ear_direito,
                        "ear_esquerdo": ear_esquerdo,
                        "estado_olhos": (
                            "CALIBRANDO" if self.olhos.calibrando
                            else "FECHADOS" if olhos_fechados else "ABERTOS"
                        ),
                        "perclos": self.olhos.perclos,
                        "perclos_valido": self.olhos.perclos_valido,
                        "cobertura_perclos": self.olhos.cobertura_perclos,
                        "tempo_observado_perclos": (
                            self.olhos.tempo_observado_perclos
                        ),
                        "olhos_fechados": olhos_fechados,
                        "tempo_olho_fechado": tempo_fechado,
                        "evento_olhos": self.olhos.ultimo_evento,
                        "frequencia_fechamentos": (
                            self.olhos.frequencia_fechamentos(agora)
                        ),
                        "frequencia_fechamentos_prolongados": (
                            self.olhos.frequencia_fechamentos_prolongados(
                                agora
                            )
                        ),

                        # Boca
                        "estado_boca": (
                            "CALIBRANDO" if self.boca.calibrando
                            else "ABERTA" if mar > self.boca.limiar_mar else "FECHADA"
                        ),
                        "boca_aberta": self.boca.inicio_bocejo is not None,
                        "bocejo": bocejo,
                        "tempo_abertura": tempo_abertura,
                        "evento_boca": self.boca.ultimo_evento,
                        "frequencia_bocejos": (
                            self.boca.frequencia_bocejos(agora)
                        ),

                        # Cabeça
                        "estado_cabeca": (
                            "CALIBRANDO" if orientacao_relativa is None
                            else "MOVIMENTO" if movimento_cabeca else "NORMAL"
                        ),
                        "movimento_cabeca": movimento_cabeca,
                        "tempo_movimento": tempo_movimento,
                        "evento_cabeca": self.detector_cabeca.ultimo_evento,
                        "frequencia_movimentos": (
                            self.detector_cabeca.frequencia_movimentos(
                                agora
                            )
                        ),
                    }

                    # Registro no CSV
                    self._adicionar_diagnostico(dados)
                    self._registrar_frame(dados, frame, numero_frame, agora)

                    # Envio dos dados para a interface
                    self.resultado_pronto.emit(dados)

        finally:
            camera.release()
            if self.telemetria is not None:
                self.telemetria.fechar()
                self.telemetria = None
            if self._coleta_ativa:
                self._coleta_ativa = False
                self.coleta_alterada.emit(False)
