import cv2
import mediapipe as mp
import time
import csv
import os
from datetime import datetime
from boca import calcular_mar, DetectorBocejo, BOCA

# Pega o caminho exato de onde este main.py está salvo (a sua pasta src)
PASTA_SRC = os.path.dirname(os.path.abspath(__file__))

# Arruma o caminho do modelo da IA
MODEL_PATH = os.path.join(PASTA_SRC, "models", "face_landmarker.task")

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

cv2.namedWindow("Detector de Bocejo", cv2.WINDOW_AUTOSIZE)

detector_bocejo = DetectorBocejo(tempo_calibracao=5)

# Arruma o caminho da telemetria e força a criação da pasta
caminho_pasta = os.path.join(PASTA_SRC, "data", "telemetry")
os.makedirs(caminho_pasta, exist_ok=True)

arquivo_csv = open(
    os.path.join(caminho_pasta, "telemetria.csv"),
    "w",
    newline="",
    encoding="utf-8"
)

logger = csv.writer(arquivo_csv)
logger.writerow(["timestamp", "tempo_execucao", "mar", "tempo_bocejando"])

inicio = time.time()

with FaceLandmarker.create_from_options(options) as landmarker:
    while True:
        ret, frame = camera.read()
        if not ret:
            print("Não foi possível capturar o frame.")
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        result = landmarker.detect(image)

        if result.face_landmarks:
            landmarks = result.face_landmarks[0]
            mar = calcular_mar(landmarks, BOCA)
            tempo_atual = time.time() - inicio
            bocejando, tempo_bocejando = detector_bocejo.atualizar(mar, tempo_atual)

            if detector_bocejo.calibrando:
                print(f"Calibrando... {tempo_atual:.1f}/{detector_bocejo.tempo_calibracao:.1f}s")
            else:
                print(f"{tempo_atual:.2f}s | MAR: {mar:.3f} | Referência: {detector_bocejo.mar_referencia:.3f} | Limiar: {detector_bocejo.limiar_mar:.3f} | Bocejando: {tempo_bocejando:.2f}s")

            logger.writerow([
                datetime.now().isoformat(),
                time.time() - inicio,
                mar,
                tempo_bocejando
            ])

            estado_boca = "BOCEJANDO" if bocejando else "NORMAL"
            cor_texto = (0, 0, 255) if bocejando else (0, 255, 0)
            texto = f"MAR: {mar:.3f} | Boca: {estado_boca} | Tempo: {tempo_bocejando:.2f}s"

            cv2.putText(frame, texto, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, cor_texto, 2)

        cv2.imshow("Detector de Bocejo", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
        if cv2.getWindowProperty("Detector de Bocejo", cv2.WND_PROP_VISIBLE) < 1:
            break

arquivo_csv.close()
camera.release()
cv2.destroyAllWindows()