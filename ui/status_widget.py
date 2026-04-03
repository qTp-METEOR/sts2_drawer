import logging

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QProgressBar
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)

class StatusWidget(QWidget):
    def __init__(self, is_dark_mode: bool = True, pause_key: str = "P", abort_key: str = "ESC"):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                            Qt.WindowType.WindowStaysOnTopHint | 
                            Qt.WindowType.Tool |
                            Qt.WindowType.WindowTransparentForInput)
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.container = QWidget(self)
        self.container.setObjectName("SolidContainer")

        if is_dark_mode:
            bg_color = "#1e1e1e"  
            border_color = "#555555"
            text_color = "#cccccc"
            prog_bg = "#2b2b2b"
        else:
            bg_color = "#f5f5f5"  
            border_color = "#cccccc"
            text_color = "#333333"
            prog_bg = "#e0e0e0"

        self.setStyleSheet(f"""
            QWidget#SolidContainer {{ background-color: {bg_color}; border-radius: 12px; border: 2px solid {border_color}; }}
            QLabel {{ background-color: transparent; border: none; color: {text_color}; }}
            QProgressBar {{ border: 1px solid {border_color}; border-radius: 5px; text-align: center; color: {text_color}; font-weight: bold; background-color: {prog_bg}; }}
            QProgressBar::chunk {{ background-color: #2e8b57; width: 10px; margin: 0.5px; }}
        """)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setSpacing(10)
        container_layout.setContentsMargins(20, 20, 20, 20)
        
        self.lbl_state = QLabel("DRAWING")
        self.lbl_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_state.setStyleSheet("color: #2e8b57; font-weight: bold; font-size: 22px;")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(25)

        self.lbl_stats = QLabel("Stroke: 0 / 0  |  ETA: Calculating...")
        self.lbl_stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_stats.setStyleSheet("font-size: 15px;")
        
        self.lbl_keys = QLabel(f"<b>[ {pause_key} ]</b> Pause  |  <b>[ {abort_key} ]</b> Abort")
        self.lbl_keys.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_keys.setStyleSheet(f"color: {text_color}; font-size: 13px;")
        
        container_layout.addWidget(self.lbl_state)
        container_layout.addWidget(self.progress_bar)
        container_layout.addWidget(self.lbl_stats)
        container_layout.addWidget(self.lbl_keys)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.container)

        self.setFixedSize(380, 170)

    def set_paused(self, is_paused: bool):
        if is_paused:
            self.lbl_state.setText("PAUSED")
            self.lbl_state.setStyleSheet("color: #ffaa00; font-weight: bold; font-size: 22px;")
        else:
            self.lbl_state.setText("DRAWING")
            self.lbl_state.setStyleSheet("color: #2e8b57; font-weight: bold; font-size: 22px;")

    def update_progress(self, current: int, total: int, percentage: int, eta: str):
        self.progress_bar.setValue(percentage)
        self.lbl_stats.setText(f"Stroke: {current} / {total}  |  ETA: {eta}")