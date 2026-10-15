import os
import random
import sys
import threading
import time

import cv2
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget
)

TEXT, MUTED = "#e7eef9", "#91a4bf"
GREEN, YELLOW, RED, BLUE = "#39d98a", "#ffca58", "#ff5d6c", "#67a9ff"

LIMIAR_EAR, LIMIAR_MAR, LIMITE_PITCH, LIMITE_YAW = 0.20, 0.70, 25, 30  

DEMO_AUTOMATICA = False   
INTERVALO_DEMO = 5000    
TEMPO_CALIBRACAO = 3.0   
MAX_CAMERAS = 6          

TELA_CHEIA = False           
CORTAR_PARA_PREENCHER = True
PAINEL_LARGURA, MARGEM = 380, 24
VIDRO = "rgba(11, 18, 32, 165)" 
VIDRO_LOG = "rgba(8, 15, 27, 150)"

PASTA = os.path.dirname(os.path.abspath(__file__))
SONS = {t: os.path.join(PASTA, "sons", f"{t}.wav") for t in ("fadiga", "atencao")}
BEEPS = {"fadiga": [(1200, 350)] * 3, "atencao": [(750, 250)]}
INTERVALO_ALERTA = {"fadiga": 4, "atencao": 6} 

ESTADOS = {
    "CALIBRANDO": dict(texto="CALIBRANDO", cor=BLUE, motivo="", ear=0.28, mar=0.05, pitch=0.0, yaw=0.0),
    "ATENTO": dict(texto="ATENTO", cor=GREEN, motivo="Nenhum sinal persistente detectado",
                   ear=0.28, mar=0.05, pitch=0.0, yaw=0.0),
    "BOCEJO": dict(texto="ATENÇÃO", cor=YELLOW, motivo="Bocejo prolongado",
                   ear=0.25, mar=0.85, pitch=-4.0, yaw=0.0),
    "CABECA": dict(texto="ATENÇÃO", cor=YELLOW, motivo="Inclinação prolongada da cabeça",
                   ear=0.27, mar=0.05, pitch=-8.0, yaw=38.0),
    "FADIGA": dict(texto="POSSÍVEL FADIGA", cor=RED, motivo="Olhos fechados por tempo prolongado",
                   ear=0.10, mar=0.05, pitch=6.0, yaw=0.0),
    "SEM_ROSTO": dict(texto="ROSTO NÃO DETECTADO", cor=YELLOW, motivo="Rosto não detectado",
                      ear=None, mar=None, pitch=None, yaw=None),
}
CICLO_DEMO = ["ATENTO", "BOCEJO", "CABECA", "FADIGA", "SEM_ROSTO"]
ATALHOS = {Qt.Key_1: "ATENTO", Qt.Key_2: "BOCEJO", Qt.Key_3: "CABECA", Qt.Key_4: "FADIGA", Qt.Key_5: "SEM_ROSTO"}


class CameraThread(QThread):
    """Só mostra a imagem da câmera, sem nenhuma análise."""
    frame_pronto = Signal(object)
    sem_camera = Signal()

    def __init__(self):
        super().__init__()
        self._executando = True

    def parar(self):
        self._executando = False
        self.wait(2500)

    def run(self):
        camera = self._abrir_camera()
        if camera is None:
            self.sem_camera.emit()
            return
        falhas = 0
        try:
            while self._executando:
                ok, frame = camera.read()
                if not ok:
                    falhas += 1
                    if falhas > 100:
                        self.sem_camera.emit()
                        return
                    self.msleep(30)
                    continue
                falhas = 0
                self.frame_pronto.emit(cv2.flip(frame, 1).copy())
        finally:
            camera.release()

    def _abrir_camera(self):
        camera, falhas = None, 0
        for i in range(MAX_CAMERAS):
            nova = self._abrir_indice(i)
            if nova is not None:
                if camera is not None:
                    camera.release()
                camera, falhas = nova, 0
            else:
                falhas += 1
                if camera is not None and falhas >= 2: 
                    break
        return camera

    @staticmethod
    def _abrir_indice(indice):
        """Abre a câmera local e confirma que ela entrega imagem; None se falhar."""
        for backend in (getattr(cv2, "CAP_DSHOW", cv2.CAP_ANY), getattr(cv2, "CAP_MSMF", cv2.CAP_ANY), cv2.CAP_ANY):
            camera = cv2.VideoCapture(indice, backend)
            if camera.isOpened():
                for prop, valor in ((cv2.CAP_PROP_FRAME_WIDTH, 640), (cv2.CAP_PROP_FRAME_HEIGHT, 480), (cv2.CAP_PROP_FPS, 30)):
                    camera.set(prop, valor)
                for _ in range(15):  
                    ok, frame = camera.read()
                    if ok and frame is not None and frame.size > 0:
                        return camera
                    time.sleep(0.1)
            camera.release()
        return None


class Interface(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monitoramento de Fadiga")
        self.resize(1280, 800)
        self.setMinimumSize(900, 560)
        self.estado = "ATENTO"
        self.thread = None
        self.som_tocando = False
        self.ultimo_alerta = {}
        self._visual_status = None
        self._inicio_calibracao = None
        self._indice_demo = 1
        self._montar_ui()
        self._estilizar()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(200)
        self.timer_demo = QTimer(self)
        self.timer_demo.timeout.connect(self._proximo_estado_demo)

        QTimer.singleShot(400, self._iniciar_camera)
        self.recalibrar()

    # ------------------------------------------------------------------ UI
    @staticmethod
    def _botao(texto, objeto, slot):
        botao = QPushButton(texto)
        botao.setObjectName(objeto)
        botao.setFocusPolicy(Qt.NoFocus) 
        botao.clicked.connect(slot)
        return botao

    @staticmethod
    def _rotulo(texto="", objeto=None, centro=False):
        rotulo = QLabel(texto)
        if objeto:
            rotulo.setObjectName(objeto)
        if centro:
            rotulo.setAlignment(Qt.AlignCenter)
            rotulo.setWordWrap(True)
        return rotulo

    def _montar_ui(self):
        self.setObjectName("janela")
        self.video = QLabel("Procurando câmera...", self)
        self.video.setObjectName("video")
        self.video.setAlignment(Qt.AlignCenter)
        self.painel = QWidget(self)
        coluna = QVBoxLayout(self.painel)
        coluna.setContentsMargins(0, 0, 0, 0)
        coluna.setSpacing(10)

        self.status_card = QFrame()
        self.status_card.setObjectName("statusCard")
        layout = QVBoxLayout(self.status_card)
        layout.setContentsMargins(16, 20, 16, 20)
        self.status_icone = self._rotulo("●", centro=True)
        self.status_texto = self._rotulo(centro=True)
        self.motivo = self._rotulo(objeto="statusReason", centro=True)
        for rotulo in (self.status_icone, self.status_texto, self.motivo):
            layout.addWidget(rotulo)
        coluna.addWidget(self.status_card)

        self.medidas = self._rotulo(objeto="measures")
        self.medidas.setWordWrap(True)
        coluna.addWidget(self.medidas)
        self._atualizar_medidas(None)

        log_card = QFrame()
        log_card.setObjectName("logCard")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(12, 10, 12, 12)
        cabecalho = QHBoxLayout()
        cabecalho.addWidget(self._rotulo("EVENTOS", "sectionTitle"))
        cabecalho.addStretch()
        cabecalho.addWidget(self._botao("Limpar", "smallButton", lambda: self.log.clear()))
        log_layout.addLayout(cabecalho)
        self.log = QTextEdit()
        self.log.setObjectName("eventLog")
        self.log.setReadOnly(True)
        log_layout.addWidget(self.log, 1)
        coluna.addWidget(log_card, 1)

        botoes = QHBoxLayout()
        botoes.setSpacing(10)
        botoes.addWidget(self._botao("Recalibrar", "glassButton", self.recalibrar), 1)
        botoes.addWidget(self._botao("Testar som", "glassButton", self.testar_som), 1)
        coluna.addLayout(botoes)
        self.painel.raise_()

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self.video.setGeometry(0, 0, self.width(), self.height())
        largura = min(PAINEL_LARGURA, self.width() // 2)
        self.painel.setGeometry(self.width() - largura - MARGEM, MARGEM, largura, self.height() - 2 * MARGEM)

    def _estilizar(self):
        borda = "border: 1px solid rgba(255, 255, 255, 45)"
        self.setStyleSheet(f"""
            QWidget {{ color: {TEXT}; font-family: Segoe UI, Arial; font-size: 12px; }}
            QWidget#janela {{ background: #000000; }}
            QLabel#sectionTitle {{ font-size: 12px; font-weight: 800; color: #c8d7ec; letter-spacing: 1px; }}
            QLabel#video {{ background: #050a12; color: {MUTED}; font-size: 18px; }}
            QLabel#statusReason {{ color: #c3d0e3; }}
            QLabel#measures {{ background: {VIDRO}; {borda}; border-radius: 10px; padding: 8px 14px; }}
            QFrame#statusCard {{ background: {VIDRO}; {borda}; border-radius: 12px; }}
            QFrame#logCard {{ background: {VIDRO_LOG}; {borda}; border-radius: 12px; }}
            QTextEdit#eventLog {{ background: transparent; border: none; color: #dbe6f5; }}
            QPushButton {{ border-radius: 9px; padding: 12px 10px; font-weight: 800; }}
            QPushButton#glassButton {{ background: {VIDRO}; {borda}; }}
            QPushButton#glassButton:hover {{ background: rgba(60, 84, 120, 190); }}
            QPushButton#smallButton {{ background: rgba(255, 255, 255, 30); color: #c3d0e3; padding: 5px 9px; }}
        """)

    # ------------------------------------------------------------ helpers
    def _definir_status(self, texto, motivo, cor):
        self.motivo.setText(motivo)
        if self._visual_status == (texto, cor):
            return
        self._visual_status = (texto, cor)
        self.status_texto.setText(texto)
        self.status_texto.setStyleSheet(f"color:{cor}; font-size:22px; font-weight:900;")
        self.status_icone.setStyleSheet(f"color:{cor}; font-size:28px;")
        self.status_card.setStyleSheet(
            f"QFrame#statusCard {{ background:{VIDRO}; border:2px solid {cor}; border-radius:12px; }}")

    def _atualizar_medidas(self, info):
        if info:
            pitch, yaw = info["pitch"], info["yaw"]
            inclinada = abs(pitch) > LIMITE_PITCH or abs(yaw) > LIMITE_YAW
            valores = [(f'{info["ear"]:.2f}', RED if info["ear"] < LIMIAR_EAR else TEXT),
                       (f'{info["mar"]:.2f}', YELLOW if info["mar"] > LIMIAR_MAR else TEXT),
                       (f"{pitch:+.0f}° / {yaw:+.0f}°", YELLOW if inclinada else TEXT)]
            detalhe = f"fecha abaixo de {LIMIAR_EAR:.2f}"
        else:
            valores, detalhe = [("—", TEXT)] * 3, ""
        nomes = ("OLHOS (EAR)", "BOCA (MAR)", "CABEÇA (cima-baixo / lados)")
        linhas = ""
        for i, (nome, (valor, cor)) in enumerate(zip(nomes, valores)):
            extra = f'<br><span style="color:{MUTED}; font-size:12px">{detalhe}</span>' if i == 0 and detalhe else ""
            linhas += (f'<tr><td style="padding:7px 0"><span style="color:{MUTED}; font-size:13px; '
                       f'font-weight:700">{nome}</span>{extra}</td><td align="right" style="padding:7px 0">'
                       f'<span style="color:{cor}; font-size:26px; font-weight:800">{valor}</span></td></tr>')
        self.medidas.setText(f'<table width="100%" cellspacing="0">{linhas}</table>')

    def registrar_evento(self, texto, tipo="info"):
        cor = {"alerta": RED, "atencao": YELLOW}.get(tipo, GREEN)
        self.log.append(f'<span style="color:{cor}">[{time.strftime("%H:%M:%S")}] {texto}</span>')

    # ------------------------------------------------------------- estados
    def set_estado(self, chave):
        if chave == self.estado and chave != "CALIBRANDO":
            return
        anterior, self.estado = self.estado, chave
        self._inicio_calibracao = time.monotonic() if chave == "CALIBRANDO" else None
        self.ultimo_alerta.clear() 
        motivo = ESTADOS[chave]["motivo"]

        if chave == "CALIBRANDO":
            self.registrar_evento("Calibrando: olhe para a frente por alguns segundos.", "atencao")
        elif anterior == "CALIBRANDO":
            self.registrar_evento("Calibração concluída. Monitorando.")
        if chave in ("BOCEJO", "CABECA"):
            self.registrar_evento("ATENÇÃO: " + motivo, "atencao")
            self.emitir_som("atencao")
        elif chave == "FADIGA":
            self.registrar_evento("FADIGA: " + motivo, "alerta")
        elif chave == "SEM_ROSTO":
            self.registrar_evento("Rosto não detectado. Ajuste a posição da câmera.", "atencao")
        self._tick()

    def recalibrar(self):
        self.timer_demo.stop()
        self.set_estado("CALIBRANDO")

    def _tick(self):
        dados = ESTADOS[self.estado]
        motivo = dados["motivo"]
        if self.estado == "CALIBRANDO":
            decorrido = time.monotonic() - self._inicio_calibracao
            if decorrido >= TEMPO_CALIBRACAO:
                self.set_estado("ATENTO")
                if DEMO_AUTOMATICA:
                    self._indice_demo = 1
                    self.timer_demo.start(INTERVALO_DEMO)
                return
            motivo = f"Olhe para a frente por alguns segundos ({decorrido:.1f}/{TEMPO_CALIBRACAO:.0f} s)"

        self._definir_status(dados["texto"], motivo, dados["cor"])
        if dados["ear"] is None:
            self._atualizar_medidas(None)
        else:
            self._atualizar_medidas({
                "ear": max(0.02, dados["ear"] + random.uniform(-0.01, 0.01)),
                "mar": max(0.0, dados["mar"] + random.uniform(-0.01, 0.01)),
                "pitch": dados["pitch"] + random.uniform(-2, 2),
                "yaw": dados["yaw"] + random.uniform(-2, 2),
            })
        if self.estado == "FADIGA":  
            self.emitir_som("fadiga")

    def _proximo_estado_demo(self):
        self.set_estado(CICLO_DEMO[self._indice_demo % len(CICLO_DEMO)])
        self._indice_demo += 1

    # -------------------------------------------------------------- câmera
    def _iniciar_camera(self):
        self.thread = CameraThread()
        self.thread.frame_pronto.connect(self._mostrar_frame)
        self.thread.sem_camera.connect(self._sem_camera)
        self.thread.start()

    def _sem_camera(self):
        self.video.setText("Sem câmera\n(a demonstração continua funcionando)")
        self.registrar_evento("Nenhuma câmera encontrada. Seguindo sem imagem.", "atencao")

    def _mostrar_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, canais = rgb.shape
        pixmap = QPixmap.fromImage(QImage(rgb.data, w, h, canais * w, QImage.Format_RGB888).copy())
        alvo = self.video.size()
        if CORTAR_PARA_PREENCHER: 
            ampliado = pixmap.scaled(alvo, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = max(0, (ampliado.width() - alvo.width()) // 2)
            y = max(0, (ampliado.height() - alvo.height()) // 2)
            self.video.setPixmap(ampliado.copy(x, y, alvo.width(), alvo.height()))
        else:
            self.video.setPixmap(pixmap.scaled(alvo, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    # ----------------------------------------------------------------- som
    def emitir_som(self, tipo="fadiga"):
        agora = time.monotonic()
        if self.som_tocando or agora - self.ultimo_alerta.get(tipo, -999) < INTERVALO_ALERTA[tipo]:
            return
        self.ultimo_alerta[tipo] = agora
        self.som_tocando = True
        threading.Thread(target=self._tocar, args=(tipo,), daemon=True).start() 

    def _tocar(self, tipo):
        try:
            try:
                import winsound
            except ImportError:
                QApplication.beep() 
                return
            if os.path.exists(SONS[tipo]):
                winsound.PlaySound(SONS[tipo], winsound.SND_FILENAME)
            else:
                for frequencia, duracao in BEEPS[tipo]:
                    winsound.Beep(frequencia, duracao)
                    time.sleep(0.1)
        except Exception:
            pass
        finally:
            self.som_tocando = False

    def testar_som(self):
        self.ultimo_alerta.clear()
        self.emitir_som("fadiga")
        self.registrar_evento("Teste do alerta de fadiga.")

    # --------------------------------------------------------------- janela
    def keyPressEvent(self, evento):
        tecla = evento.key()
        if tecla in ATALHOS:
            self.set_estado(ATALHOS[tecla])
        elif tecla == Qt.Key_R:
            self.recalibrar()
        elif tecla == Qt.Key_F11:
            self.showNormal() if self.isFullScreen() else self.showFullScreen()
        elif tecla == Qt.Key_Escape and self.isFullScreen():
            self.showNormal()
        else:
            super().keyPressEvent(evento)

    def closeEvent(self, evento):
        self.timer.stop()
        self.timer_demo.stop()
        if self.thread and self.thread.isRunning():
            self.thread.parar()
        evento.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    janela = Interface()
    janela.showFullScreen() if TELA_CHEIA else janela.show()
    sys.exit(app.exec())