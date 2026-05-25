from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QCloseEvent, QMovie, QMouseEvent, QPaintEvent, QPainter, QPixmap
from PySide6.QtWidgets import QSplashScreen

class AnimatedSplashScreen(QSplashScreen):
    def __init__(self, gif_path: str, target_width: int = 500) -> None:
        self.movie = QMovie(gif_path)
        self.movie.jumpToFrame(0)

        orig = self.movie.currentPixmap()
        scale = target_width / orig.width()
        self.target_size = QSize(
            int(orig.width() * scale), int(orig.height() * scale)
        )

        self.movie.setScaledSize(self.target_size)

        placeholder = QPixmap(self.target_size)
        placeholder.fill(Qt.GlobalColor.transparent)
        super().__init__(
            placeholder,
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint,
        )

        self.setFixedSize(self.target_size)
        self.movie.frameChanged.connect(self.update)
        self.movie.start()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        pass

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.movie.currentPixmap())

    def closeEvent(self, event: QCloseEvent) -> None:
        self.movie.stop()
        super().closeEvent(event)