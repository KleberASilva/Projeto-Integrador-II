import cv2
import mediapipe as mp
import math
import time
import csv
from datetime import datetime

MODEL_PATH = "src/models/face_landmarker.task"


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

    ear = (
        distancia_vertical_1 +
        distancia_vertical_2
    ) / (2 * distancia_horizontal)

    return ear


# Pontos dos olhos
olho_direito = [33, 159, 145, 133, 153, 160]
olho_esquerdo = [362, 386, 380, 263, 374, 385]


BaseOptions = mp.tasks.BaseOptions
FaceLandmarker = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode


options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=VisionRunningMode.IMAGE,
    num_faces=1
)


camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Não foi possível acessar a câmera.")
    exit()

valores_ear = []
limiar_ear = 0.19
arquivo_csv = open(
    "src/data/telemetry/telemetria.csv",
    "w",
    newline="",
    encoding="utf-8"
)

logger = csv.writer(arquivo_csv)

logger.writerow([
    "timestamp",
    "tempo_execucao",
    "ear_direito",
    "ear_esquerdo",
    "ear_medio",
    "tempo_olho_fechado"
])

inicio = time.time()
inicio_olho_fechado = None

with FaceLandmarker.create_from_options(options) as landmarker:

    while True:

        ret, frame = camera.read()

        if not ret:
            print("Não foi possível capturar o frame.")
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=frame_rgb
        )

        result = landmarker.detect(image)

        if result.face_landmarks:

            landmarks = result.face_landmarks[0]

            ear_direito = calcular_ear(
                landmarks,
                olho_direito
            )

            ear_esquerdo = calcular_ear(
                landmarks,
                olho_esquerdo
            )

            ear_medio = (
                ear_direito +
                ear_esquerdo
            ) / 2

            if ear_medio < limiar_ear:
                if inicio_olho_fechado is None:
                    inicio_olho_fechado = time.time()
                tempo_olho_fechado = time.time() - inicio_olho_fechado
            else:
                inicio_olho_fechado = None
                tempo_olho_fechado = 0

            logger.writerow([
                datetime.now().isoformat(),
                time.time() - inicio,
                ear_direito,
                ear_esquerdo,
                ear_medio,
                tempo_olho_fechado
            ])

            valores_ear.append(ear_medio)

            print(
                f"{time.time() - inicio:.2f}s | "
                f"EAR: {ear_medio:.3f} | "
                f"Fechado: {tempo_olho_fechado:.2f}s"
            )

            texto = (
                f"EAR: {ear_medio:.3f} | "
                f"Fechado: {tempo_olho_fechado:.2f}s"
            )

            cv2.putText(
                frame,
                texto,
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )

        cv2.imshow("Face Landmarker", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        if cv2.getWindowProperty(
            "Face Landmarker",
            cv2.WND_PROP_VISIBLE
        ) < 1:
            break

arquivo_csv.close()
camera.release()
cv2.destroyAllWindows()