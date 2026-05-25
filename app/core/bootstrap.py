import sys
from typing import Any

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.ui.splash import AnimatedSplashScreen
from app.utils.paths import get_resource_path

class ModelLoaderThread(QThread):
    model_ready = Signal(object)

    def run(self) -> None:
        try:
            from rembg import new_session  # type: ignore

            session = new_session("isnet-general-use")
            self.model_ready.emit(session)

        except Exception as e:
            print(f"Background engine warm-up failed: {e}")
            self.model_ready.emit(None)

class AppOrchestrator:
    def __init__(self) -> None:
        self.app = QApplication(sys.argv)
        self.app.setWindowIcon(
            QIcon(str(get_resource_path("app/resources/images/icon.ico")))
        )

        self.splash = AnimatedSplashScreen(
            str(get_resource_path("app/resources/images/splash.gif"))
        )
        self.splash.show()

        self.main_window: Any = None

        self.loader = ModelLoaderThread()
        self.loader.model_ready.connect(self._on_boot_complete)
        self.loader.finished.connect(self.loader.deleteLater)
        self.loader.start()

    def _on_boot_complete(self, session_data: Any) -> None:
        from app.ui.main_window import MainWindow

        self.main_window = MainWindow(rembg_session=session_data)
        self.main_window.show()
        self.main_window.raise_()

        self.splash.finish(self.main_window)