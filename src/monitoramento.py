
import os
import time

import cv2
import mediapipe as mp

from PySide6.QtCore import QThread, Signal

from eye_detection import detectar_olhos, DetectorOlhos
from boca import BOCA, calcular_mar, DetectorBocejo
from head_pose import estimar_orientacao, FiltroOrientacao


MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "models",
    "face_landmarker.task"
)


class MonitoramentoThread(QThread):
    frame_pronto = Signal(object)
    resultado_pronto = Signal(object)
    sem_camera = Signal()

    def __init__(self):
        super().__init__()
        self._executando = True
        self._recalibrar = False

    def parar(self):
        self._executando = False
        self.wait()

    def solicitar_recalibracao(self):
        self._recalibrar = True

    def _criar_detectores(self):
        self.olhos = DetectorOlhos(tempo_calibracao=5)
        self.boca = DetectorBocejo(tempo_calibracao=5)
        self.cabeca = FiltroOrientacao()

    def run(self):
        self._criar_detectores()

        camera = cv2.VideoCapture(0)

        if not camera.isOpened():
            self.sem_camera.emit()
            return

        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(
                model_asset_path=MODEL_PATH
            ),
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_faces=1
        )

        with mp.tasks.vision.FaceLandmarker.create_from_options(options) as landmarker:
            try:
                while self._executando:
                    if self._recalibrar:
                        self._criar_detectores()
                        self._recalibrar = False

                    ok, frame = camera.read()

                    if not ok:
                        continue

                    frame = cv2.flip(frame, 1)
                    altura, largura = frame.shape[:2]

                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    imagem = mp.Image(
                        image_format=mp.ImageFormat.SRGB,
                        data=rgb
                    )

                    resultado = landmarker.detect(imagem)

                    self.frame_pronto.emit(frame.copy())

                    if not resultado.face_landmarks:
                        self.resultado_pronto.emit({
                            "estado": "SEM_ROSTO",
                            "ear": None,
                            "mar": None,
                            "pitch": None,
                            "yaw": None,
                        })
                        continue

                    landmarks = resultado.face_landmarks[0]
                    agora = time.monotonic()

                    # Olhos
                    _, _, ear = detectar_olhos(landmarks)

                    olhos_fechados, tempo_fechado = self.olhos.atualizar(
                        ear, agora
                    )

                    # Boca
                    mar = calcular_mar(landmarks, BOCA)

                    bocejo, _ = self.boca.atualizar(mar, agora)

                    # Cabeça
                    orientacao = estimar_orientacao(
                        landmarks, largura, altura
                    )

                    orientacao_filtrada = self.cabeca.atualizar(orientacao)
                    orientacao_relativa = self.cabeca.calibrar(
                        orientacao_filtrada
                    )

                    calibrando = (
                        self.olhos.calibrando
                        or self.boca.calibrando
                        or orientacao_relativa is None
                    )

                    pitch = None
                    yaw = None

                    if orientacao_relativa is not None:
                        yaw, pitch, _ = orientacao_relativa

                    if calibrando:
                        estado = "CALIBRANDO"
                    elif olhos_fechados and tempo_fechado >= 1.5:
                        estado = "FADIGA"
                    elif bocejo:
                        estado = "BOCEJO"
                    elif (
                        pitch is not None
                        and (abs(pitch) > 25 or abs(yaw) > 30)
                    ):
                        estado = "CABECA"
                    else:
                        estado = "ATENTO"

                    self.resultado_pronto.emit({
                        "estado": estado,
                        "ear": ear,
                        "mar": mar,
                        "pitch": pitch,
                        "yaw": yaw,
                        "limiar_ear": self.olhos.limiar_ear,
                        "limiar_mar": self.boca.limiar_mar,
                        "tempo_olho_fechado": tempo_fechado,
                    })

            finally:
                camera.release()
