import sys
from PySide6.QtWidgets import QApplication
from interface import Interface


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    janela = Interface()
    janela.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
