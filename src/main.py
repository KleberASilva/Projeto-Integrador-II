import cv2
import mediapipe as mp
import time
import csv
from datetime import datetime
from eye_detection import detectar_olhos

MODEL_PATH = "src/models/face_landmarker.task"

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

            ear_direito, ear_esquerdo, ear_medio = detectar_olhos(landmarks)

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