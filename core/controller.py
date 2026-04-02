from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication
from core.worker import DrawingWorker
from ui.status_widget import StatusWidget
from utils.keybinds import parse_keybind_string
from core.config import config
from utils.theme import is_theme_dark

class DrawingController(QObject):
    """Orchestrates the drawing worker thread and the HUD overlay."""
    draw_completed = Signal()
    draw_aborted = Signal()
    draw_error = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.worker = None
        self.hud = None

    def start_drawing(self, strokes: list, offset_x: int, offset_y: int):
        pause_key_str = config.pause_key
        abort_key_str = config.abort_key
        
        pause_vks = parse_keybind_string(pause_key_str)
        abort_vks = parse_keybind_string(abort_key_str)

        is_dark = is_theme_dark(config.theme)
        
        self.hud = StatusWidget(is_dark_mode=is_dark, pause_key=pause_key_str, abort_key=abort_key_str)
        
        screen_rect = QApplication.primaryScreen().geometry()
        self.hud.move(screen_rect.width() - self.hud.width() - 20, 20)
        self.hud.show()

        delay_ms = config.drawing_delay

        self.worker = DrawingWorker(strokes, offset_x, offset_y, abort_vks=abort_vks, pause_vks=pause_vks, delay_ms=delay_ms)
        self.worker.progress.connect(self.hud.update_progress)
        self.worker.status_changed.connect(self.hud.set_paused)
        self.worker.draw_completed.connect(self.on_complete)
        self.worker.aborted.connect(self.on_aborted)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def cleanup(self):
        if self.hud:
            self.hud.close()
            self.hud = None

    def on_complete(self):
        self.cleanup()
        self.draw_completed.emit()

    def on_aborted(self):
        self.cleanup()
        self.draw_aborted.emit()

    def on_error(self, err_msg: str):
        self.cleanup()
        self.draw_error.emit(err_msg)