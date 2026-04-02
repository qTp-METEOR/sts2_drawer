import sys
from PySide6.QtWidgets import QApplication

# Initialize core utilities before loading UI modules
from utils.logger import setup_logger

from ui.main_window import MainWindow

def main():
    setup_logger()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()