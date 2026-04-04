from typing import Optional
import logging

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPaintEvent, QMouseEvent, QPainter, QColor, QPen
from PySide6.QtCore import QPoint, Qt, QRect, Signal

from app.core import hardware_api

logger = logging.getLogger(__name__)

class SelectionOverlay(QWidget):
    area_selected = Signal(int, int, int, int) 

    def __init__(self):
        super().__init__()
        logger.debug("Initializing SelectionOverlay...")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        x, y, w, h = hardware_api.get_virtual_screen_bounds()
        
        logger.info(f"Hardware Virtual Screen Bounds: X:{x}, Y:{y}, W:{w}, H:{h}")
        self.setGeometry(x, y, w, h)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self.start_global: Optional[QPoint] = None
        self.start_local: Optional[QPoint] = None
        self.selection_rect_local = QRect()

        self.show()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 160))

        if not self.selection_rect_local.isNull():
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(self.selection_rect_local, Qt.GlobalColor.transparent)
            
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            pen = QPen(QColor(0, 255, 0), 2)
            painter.setPen(pen)
            painter.drawRect(self.selection_rect_local)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_global = event.globalPosition().toPoint()
            self.start_local = self.mapFromGlobal(self.start_global)
            self.selection_rect_local = QRect(self.start_local, self.start_local)
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.start_local:
            current_local = self.mapFromGlobal(event.globalPosition().toPoint())
            self.selection_rect_local = QRect(self.start_local, current_local).normalized()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.start_global:
            end_global = event.globalPosition().toPoint()
            final_rect = QRect(self.start_global, end_global).normalized()
            
            self.area_selected.emit(final_rect.x(), final_rect.y(), final_rect.width(), final_rect.height())
            self.close()