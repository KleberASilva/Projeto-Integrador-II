
import sys

from PySide6.QtWidgets import QApplication
from interface import Interface, TELA_CHEIA


def main():
    app = QApplication(sys.argv)

    janela = Interface()

    if TELA_CHEIA:
        janela.showFullScreen()
    else:
        janela.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
