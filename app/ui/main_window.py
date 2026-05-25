import os
import logging
from pathlib import Path
from typing import Any, Optional, List, Tuple, cast

import cv2
import numpy as np
from numpy.typing import NDArray
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QPushButton, QLabel, QFileDialog, QHBoxLayout, 
                               QMessageBox, QTabWidget)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QAction

from app.utils.logger import signaler
from app.utils.theme import is_theme_dark, apply_native_titlebar_theme
from app.engine.image_processor import ImageProcessor
from app.engine.text_processor import TextProcessor
from app.ui.selection_overlay import SelectionOverlay
from app.ui.settings_dialog import SettingsDialog
from app.ui.image_setup_widget import ImageModeWidget
from app.ui.text_setup_widget import TextModeWidget
from app.core.config import config
from app.core.controller import DrawingController

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self, rembg_session: Optional[Any] = None) -> None:
        super().__init__()
        self.setWindowTitle("StS2 Drawer")
        self.setMinimumSize(950, 650) 
        
        self.current_theme = config.theme
        signaler.error_signal.connect(self.show_critical_error)

        self.image_processor = ImageProcessor(rembg_session=rembg_session)
        self.text_processor = TextProcessor()
        
        self.image_path: Optional[str] = None
        self.draw_area: Optional[Tuple[int, int, int, int]] = None
        self.current_strokes: List[NDArray[np.int32]] = []

        self.controller = DrawingController(self)
        self.controller.draw_completed.connect(self.on_draw_complete)
        self.controller.draw_aborted.connect(self.on_draw_aborted)
        self.controller.draw_error.connect(self.on_draw_error)
        
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.update_live_preview)

        self.setup_menu_bar()
        self.setup_ui()
        self.load_stylesheet()
        self.force_focus()

    def show_themed_messagebox(self, title: str, text: str, icon: QMessageBox.Icon) -> None:
        self.reset_ui()
        self.force_focus()
        
        msg = QMessageBox(self) 
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(icon)
        
        is_dark = is_theme_dark(self.current_theme)
        apply_native_titlebar_theme(int(msg.winId()), is_dark)
        
        msg.exec()

    def show_critical_error(self, title: str, message: str) -> None:
        self.show_themed_messagebox(title, f"An unexpected error occurred:\n\n{message}", QMessageBox.Icon.Critical)

    def setup_menu_bar(self) -> None:
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        
        action_load = QAction("Load Image...", self)
        action_load.setShortcut("Ctrl+O")
        action_load.triggered.connect(self.load_image)
        file_menu.addAction(action_load)
        file_menu.addSeparator()
        
        action_exit = QAction("Exit", self)
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)

        edit_menu = menu_bar.addMenu("Edit")
        action_settings = QAction("Settings...", self)
        action_settings.triggered.connect(self.open_settings)
        edit_menu.addAction(action_settings)

    def setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        control_panel = QWidget()
        control_panel.setMinimumWidth(350)
        control_panel.setMaximumWidth(550)
        v_layout = QVBoxLayout(control_panel)

        self.tabs = QTabWidget()
        self.image_tab = ImageModeWidget(initial_delay=config.drawing_delay)
        self.text_tab = TextModeWidget()
        
        self.tabs.addTab(self.image_tab, "Image Mode")
        self.tabs.addTab(self.text_tab, "Text Mode")
        
        self.tabs.currentChanged.connect(self._on_tab_changed)
        
        self.image_tab.load_requested.connect(self.load_image)
        self.image_tab.settings_changed.connect(self._on_settings_changed)
        self.image_tab.bg_toggled.connect(self.on_bg_toggle_changed)
        self.image_tab.delay_changed.connect(self.set_drawing_delay)
        
        self.text_tab.settings_changed.connect(self._on_settings_changed)

        v_layout.addWidget(self.tabs)
        v_layout.addSpacing(10)

        self.lbl_area = QLabel("Target: Not Selected")
        self.lbl_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_select_area = QPushButton("Select Draw Area")
        self.btn_select_area.clicked.connect(self.open_overlay)
        self.btn_select_area.setEnabled(True) 
        
        v_layout.addWidget(self.btn_select_area)
        v_layout.addWidget(self.lbl_area)
        v_layout.addSpacing(10)

        self.lbl_stats = QLabel("Strokes: 0 | Points: 0")
        self.lbl_stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_stats.setObjectName("StatsLabel")
        v_layout.addWidget(self.lbl_stats)
        
        self.btn_start = QPushButton("START DRAWING")
        self.btn_start.setObjectName("StartBtn")
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self.start_drawing)
        v_layout.addWidget(self.btn_start)

        preview_panel = QWidget()
        preview_layout = QVBoxLayout(preview_panel)
        
        self.lbl_preview = QLabel("Select an area to see preview.")
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setObjectName("PreviewLabel")
        preview_layout.addWidget(self.lbl_preview)

        main_layout.addWidget(control_panel, stretch=1)
        main_layout.addWidget(preview_panel, stretch=2)

    def _on_tab_changed(self, index: int) -> None:
        self.preview_timer.start(100)

    def _on_settings_changed(self) -> None:
        self.preview_timer.start(200)

    def set_drawing_delay(self, val: int) -> None:
        config.drawing_delay = val

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.current_theme, self)
        dialog.theme_changed.connect(self.change_theme)
        dialog.exec() 

    def change_theme(self, new_theme: str) -> None:
        self.current_theme = new_theme
        config.theme = new_theme 
        self.load_stylesheet()
        self.update_live_preview() 
        logger.info(f"Theme changed to: {new_theme}")

    def get_resolved_theme(self) -> str:
        if self.current_theme == "System Default":
            scheme = QApplication.styleHints().colorScheme()
            if scheme == Qt.ColorScheme.Dark:
                return "Dark"
            return "Light"
        return self.current_theme

    def load_stylesheet(self) -> None:
        is_dark = is_theme_dark(self.current_theme)
        apply_native_titlebar_theme(int(self.winId()), is_dark)
        
        file_name = "dark.qss" if is_dark else "light.qss"
        base_path = Path(__file__).resolve().parent.parent
        style_path = base_path / "resources" / "styles" / file_name
        
        try:
            with open(str(style_path), "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            logger.error(f"Stylesheet not found: {style_path}. Ensure the file exists.")

    def load_image(self) -> None:
        self.tabs.setCurrentIndex(0) 
        
        file_name, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Image", 
            config.last_open_dir, 
            "Images (*.png *.jpg *.jpeg *.webp *.avif *.bmp *.heic *.heif *.tiff *.tif *.ico)"
        )
        
        if file_name:
            config.last_open_dir = os.path.dirname(file_name)
            self.image_path = file_name
            self.image_tab.set_load_button_text("Processing Image...")
            QApplication.processEvents()

            settings = self.image_tab.get_settings()
            if self.image_processor.load_image(self.image_path):
                self.image_processor.process_background(settings["remove_bg"])
                self.image_tab.enable_controls(True)
                self.update_live_preview()
            else:
                self.show_themed_messagebox(
                    "Format Error", 
                    "Could not decode this image format.", 
                    QMessageBox.Icon.Warning
                )
            
            self.image_tab.set_load_button_text("Load Image")

    def on_bg_toggle_changed(self, remove_bg: bool) -> None:
        if not self.image_path: return
        self.image_tab.set_load_button_text("Updating Background...")
        self.image_tab.enable_controls(False)
        QApplication.processEvents()
        
        self.image_processor.process_background(remove_bg)
        
        self.image_tab.enable_controls(True)
        self.image_tab.set_load_button_text("Load Image")
        self.update_live_preview()

    def open_overlay(self) -> None:
        self.hide() 
        self.overlay = SelectionOverlay()
        self.overlay.area_selected.connect(self.on_area_selected)

    def on_area_selected(self, x: int, y: int, w: int, h: int) -> None:
        self.draw_area = (x, y, w, h)
        self.lbl_area.setText(f"Target: W:{w}px, H:{h}px")
        self.show() 
        self.update_live_preview()

    def update_live_preview(self) -> None:
        if not self.draw_area:
            self.lbl_preview.setText("Select Draw Area to define your canvas.")
            self.btn_start.setEnabled(False)
            return

        _, _, w, h = self.draw_area
        is_dark = (self.get_resolved_theme() == "Dark")
        line_color = (255, 255, 255) if is_dark else (0, 0, 0)
        
        preview_img = None
        points = 0

        if self.tabs.currentIndex() == 0:
            if not self.image_path:
                self.lbl_preview.setText("Click 'Load Image' to select a picture to draw.")
                self.btn_start.setEnabled(False)
                return
                
            settings = self.image_tab.get_settings()
            preview_img, points = self.image_processor.generate_preview(
                w, h, settings["thresh1"], settings["thresh2"], settings["speed"], line_color=line_color
            )
            self.current_strokes = self.image_processor.current_strokes

        elif self.tabs.currentIndex() == 1:
            settings = self.text_tab.get_settings()
            if not settings["text"].strip():
                self.lbl_preview.setText("Enter some text in the input box to see the preview.")
                self.btn_start.setEnabled(False)
                return

            strokes, points = self.text_processor.generate_strokes(
                settings["text"], settings["font_family"], settings["font_size"],
                w, h, settings["alignment"]
            )
            self.current_strokes = strokes
            preview_img = self.render_raw_strokes_to_image(strokes, w, h, line_color)

        if preview_img is not None and self.current_strokes:
            self.lbl_stats.setText(f"Strokes: {len(self.current_strokes):,} | Points: {points:,}")
            
            h_img, w_img, ch = preview_img.shape
            bytes_per_line = ch * w_img
            qt_image = QImage(preview_img.data, w_img, h_img, bytes_per_line, QImage.Format.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qt_image)
            
            self.lbl_preview.setPixmap(pixmap.scaled(self.lbl_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.btn_start.setEnabled(True)
        else:
            self.lbl_preview.setText("Could not generate preview. Try adjusting your settings.")
            self.btn_start.setEnabled(False)
        
    def render_raw_strokes_to_image(
        self, strokes: List[NDArray[np.int32]], w: int, h: int, line_color: Tuple[int, int, int]
    ) -> NDArray[np.uint8]:
        """Used by the text processor to convert raw math arrays into a previewable RGBA image."""
        preview = np.zeros((h, w, 4), dtype=np.uint8)
        color_alpha: Tuple[int, int, int, int] = (*line_color, 255) 
        for stroke in strokes:
            cv2.polylines(preview, [stroke], isClosed=False, color=color_alpha, thickness=1, lineType=cv2.LINE_AA)

        return cast(NDArray[np.uint8], cv2.cvtColor(preview, cv2.COLOR_BGRA2RGBA))
    
    def force_focus(self) -> None:
        if self.isMinimized():
            self.showNormal()
        self.setWindowState((self.windowState() & ~Qt.WindowState.WindowMinimized) | Qt.WindowState.WindowActive)
        self.raise_()           
        self.activateWindow()

    def start_drawing(self) -> None:
        if not self.draw_area or not self.current_strokes:
            return

        x, y, _, _ = self.draw_area
        
        self.tabs.setEnabled(False)
        self.btn_select_area.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.btn_start.setText("DRAWING...")
        
        self.controller.start_drawing(self.current_strokes, x, y)

    def on_draw_complete(self) -> None:
        self.show_themed_messagebox("Success", "Drawing completed!", QMessageBox.Icon.Information)

    def on_draw_aborted(self) -> None:
        self.show_themed_messagebox("Aborted", "Drawing stopped by user.", QMessageBox.Icon.Warning)

    def on_draw_error(self, err_msg: str) -> None:
        self.show_themed_messagebox("Error", f"An error occurred:\n{err_msg}", QMessageBox.Icon.Critical)

    def reset_ui(self) -> None:
        self.tabs.setEnabled(True)
        self.btn_select_area.setEnabled(True)
        self.btn_start.setEnabled(True)
        self.btn_start.setText("START DRAWING")
