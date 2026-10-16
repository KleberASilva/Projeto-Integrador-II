import cv2
import mediapipe as mp
import time
import csv
from datetime import datetime
from eye_detection import detectar_olhos, DetectorOlhos

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

camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

cv2.namedWindow("Face Landmarker", cv2.WINDOW_AUTOSIZE)

detector_olhos = DetectorOlhos(tempo_calibracao=5)

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

            tempo_atual = time.time() - inicio

            olhos_fechados, tempo_olho_fechado = detector_olhos.atualizar(
                ear_medio,
                tempo_atual
            )

            if detector_olhos.calibrando:
                print(
                    f"Calibrando... "
                    f"{tempo_atual:.1f}/{detector_olhos.tempo_calibracao:.1f}s"
                )
            else:
                print(
                    f"{tempo_atual:.2f}s | "
                    f"EAR: {ear_medio:.3f} | "
                    f"Referência: {detector_olhos.ear_referencia:.3f} | "
                    f"Limiar: {detector_olhos.limiar_ear:.3f} | "
                    f"Fechado: {tempo_olho_fechado:.2f}s"
                )

            logger.writerow([
                datetime.now().isoformat(),
                time.time() - inicio,
                ear_direito,
                ear_esquerdo,
                ear_medio,
                tempo_olho_fechado
            ])

            estado_olhos = "FECHADOS" if olhos_fechados else "ABERTOS"

            texto = (
                f"EAR: {ear_medio:.3f} | "
                f"Olhos: {estado_olhos} | "
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