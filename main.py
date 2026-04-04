import sys

from PySide6.QtWidgets import QApplication

from app.utils.logger import setup_logger
from app.ui.main_window import MainWindow

def main():
    setup_logger()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()