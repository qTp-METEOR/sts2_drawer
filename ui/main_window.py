import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QPushButton, QLabel, QFileDialog, QSlider, QHBoxLayout, 
                               QMessageBox, QCheckBox, QGroupBox, QFormLayout, 
                               QSpinBox, QDoubleSpinBox, QSizePolicy)
from PySide6.QtCore import QStandardPaths, Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QAction

from utils.logger import signaler, logger
from utils.theme import is_theme_dark, apply_native_titlebar_theme
from engine.image_processor import ImageProcessor
from ui.operating_overlay import SelectionOverlay
from ui.settings_dialog import SettingsDialog
from core.config import config
from core.controller import DrawingController

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Auto Drawer Pro - Studio")
        self.setMinimumSize(950, 650) 
        
        self.current_theme = config.theme
        signaler.error_signal.connect(self.show_critical_error)

        self.processor = ImageProcessor()
        self.image_path = None
        self.draw_area = None

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

    def show_themed_messagebox(self, title: str, text: str, icon: QMessageBox.Icon):
        self.reset_ui()
        self.force_focus()
        
        msg = QMessageBox(self) 
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(icon)
        
        is_dark = is_theme_dark(self.current_theme)
        apply_native_titlebar_theme(int(msg.winId()), is_dark)
        
        msg.exec()

    def show_critical_error(self, title: str, message: str):
        self.show_themed_messagebox(title, f"An unexpected error occurred:\n\n{message}", QMessageBox.Icon.Critical)

    def setup_menu_bar(self):
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

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        control_panel = QWidget()
        control_panel.setMinimumWidth(350)
        control_panel.setMaximumWidth(550)
        v_layout = QVBoxLayout(control_panel)

        self.btn_load_image = QPushButton("1. Load Image")
        self.btn_load_image.clicked.connect(self.load_image)
        v_layout.addWidget(self.btn_load_image)

        self.lbl_area = QLabel("Target: Not Selected")
        self.lbl_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_select_area = QPushButton("2. Select Draw Area")
        self.btn_select_area.clicked.connect(self.open_overlay)
        self.btn_select_area.setEnabled(False)
        v_layout.addWidget(self.btn_select_area)
        v_layout.addWidget(self.lbl_area)
        v_layout.addSpacing(10)

        settings_group = QGroupBox("Processing Settings")
        form_layout = QFormLayout(settings_group)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.chk_remove_bg = QCheckBox("AI Background Removal")
        self.chk_remove_bg.setChecked(True)
        self.chk_remove_bg.setEnabled(False)
        self.chk_remove_bg.stateChanged.connect(self.on_bg_toggle_changed)
        form_layout.addRow("", self.chk_remove_bg)

        self.slider_thresh1, self.spin_thresh1 = self.create_setting_row(form_layout, "Canny Min:", 0, 255, 50)
        self.slider_thresh2, self.spin_thresh2 = self.create_setting_row(form_layout, "Canny Max:", 0, 255, 100)
        self.slider_speed, self.spin_speed = self.create_setting_row(form_layout, "Speed/Detail:", 1, 100, 10, is_float=True)
        self.slider_delay, self.spin_delay = self.create_setting_row(form_layout, "Click Delay (ms):", 1, 20, config.drawing_delay)

        self.spin_delay.valueChanged.connect(lambda val: setattr(config, 'drawing_delay', val))

        self.btn_reset = QPushButton("↺ Reset Defaults")
        self.btn_reset.setEnabled(False)
        self.btn_reset.clicked.connect(self.reset_to_defaults)
        form_layout.addRow("", self.btn_reset)

        v_layout.addWidget(settings_group)

        self.lbl_stats = QLabel("Strokes: 0 | Points: 0")
        self.lbl_stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_stats.setObjectName("StatsLabel")
        v_layout.addWidget(self.lbl_stats)
        v_layout.addStretch()

        self.btn_start = QPushButton("3. START DRAWING")
        self.btn_start.setObjectName("StartBtn")
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self.start_drawing)
        v_layout.addWidget(self.btn_start)

        preview_panel = QWidget()
        preview_layout = QVBoxLayout(preview_panel)
        
        self.lbl_preview = QLabel("Load an image and select an area to see preview.")
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setObjectName("PreviewLabel")
        preview_layout.addWidget(self.lbl_preview)

        main_layout.addWidget(control_panel, stretch=1)
        main_layout.addWidget(preview_panel, stretch=2)

    def create_setting_row(self, layout: QFormLayout, label_name: str, min_val: int, max_val: int, default_val: int, is_float: bool = False):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        slider.setEnabled(False)

        if is_float:
            spin_box = QDoubleSpinBox()
            spin_box.setRange(min_val / 10.0, max_val / 10.0)
            spin_box.setSingleStep(0.1)
            spin_box.setDecimals(1)
            spin_box.setSuffix("x")
            spin_box.setValue(default_val / 10.0)
        else:
            spin_box = QSpinBox()
            spin_box.setRange(min_val, max_val)
            spin_box.setValue(default_val)

        spin_box.setMinimumWidth(85)
        spin_box.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        spin_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spin_box.setEnabled(False)

        def on_slider_changed(val):
            spin_box.blockSignals(True) 
            spin_box.setValue(val / 10.0 if is_float else val)
            spin_box.blockSignals(False)
            self.preview_timer.start(200)

        def on_spin_changed(val):
            slider.blockSignals(True) 
            slider.setValue(int(val * 10) if is_float else int(val))
            slider.blockSignals(False)
            self.preview_timer.start(200)

        slider.valueChanged.connect(on_slider_changed)
        spin_box.valueChanged.connect(on_spin_changed)

        h_layout = QHBoxLayout()
        h_layout.addWidget(slider)
        h_layout.addWidget(spin_box)
        h_layout.setContentsMargins(0, 0, 0, 0)
        layout.addRow(label_name, h_layout)
        
        return slider, spin_box

    def open_settings(self):
        dialog = SettingsDialog(self.current_theme, self)
        dialog.theme_changed.connect(self.change_theme)
        dialog.exec() 

    def change_theme(self, new_theme: str):
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

    def load_stylesheet(self):
        is_dark = is_theme_dark(self.current_theme)
        apply_native_titlebar_theme(int(self.winId()), is_dark)
        
        file_name = "dark.qss" if is_dark else "light.qss"
        style_path = os.path.join("resources", "styles", file_name)
        
        try:
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            logger.error(f"Stylesheet not found: {style_path}. Ensure the file exists.")

    def enable_controls(self, state: bool):
        self.chk_remove_bg.setEnabled(state)
        self.slider_thresh1.setEnabled(state)
        self.spin_thresh1.setEnabled(state)
        self.slider_thresh2.setEnabled(state)
        self.spin_thresh2.setEnabled(state)
        self.slider_speed.setEnabled(state)
        self.spin_speed.setEnabled(state)
        self.slider_delay.setEnabled(state)
        self.spin_delay.setEnabled(state)
        self.btn_reset.setEnabled(state)
        self.btn_start.setEnabled(state and self.draw_area is not None)

    def reset_to_defaults(self):
        self.slider_thresh1.setValue(50)
        self.slider_thresh2.setValue(100)
        self.slider_speed.setValue(10)
        
        if not self.chk_remove_bg.isChecked():
            self.chk_remove_bg.setChecked(True)
        else:
            self.update_live_preview() 

    def load_image(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Image", 
            config.last_open_dir, 
            "Images (*.png *.jpg *.jpeg *.webp *.avif *.bmp *.heic *.heif *.tiff *.tif *.ico)"
        )
        
        if file_name:
            config.last_open_dir = os.path.dirname(file_name)

            self.image_path = file_name
            self.btn_load_image.setText("Processing Image...")
            QApplication.processEvents()

            if self.processor.load_image(self.image_path):
                self.processor.process_background(self.chk_remove_bg.isChecked())
                self.btn_select_area.setEnabled(True)
                self.enable_controls(True)
                self.update_live_preview()
            else:
                self.show_themed_messagebox(
                    "Format Error", 
                    "Could not decode this image format. It may be unsupported or corrupted.", 
                    QMessageBox.Icon.Warning
                )
            
            self.btn_load_image.setText("1. Load Image")

    def on_bg_toggle_changed(self):
        if not self.image_path: return
        self.btn_load_image.setText("Updating Background...")
        self.enable_controls(False)
        QApplication.processEvents()
        
        self.processor.process_background(self.chk_remove_bg.isChecked())
        
        self.enable_controls(True)
        self.btn_load_image.setText("1. Load Image")
        self.update_live_preview()

    def open_overlay(self):
        self.hide() 
        self.overlay = SelectionOverlay()
        self.overlay.area_selected.connect(self.on_area_selected)

    def on_area_selected(self, x, y, w, h):
        self.draw_area = (x, y, w, h)
        self.lbl_area.setText(f"Target: W:{w}px, H:{h}px")
        self.show() 
        self.enable_controls(True)
        self.update_live_preview()

    def update_live_preview(self):
        if not self.image_path or not self.draw_area:
            return

        x, y, w, h = self.draw_area
        t1 = self.slider_thresh1.value()
        t2 = self.slider_thresh2.value()
        speed = self.slider_speed.value() / 10.0

        is_dark = (self.get_resolved_theme() == "Dark")
        line_color = (255, 255, 255) if is_dark else (0, 0, 0)
        
        preview_img, points = self.processor.generate_preview(w, h, t1, t2, speed, line_color=line_color)
        
        if preview_img is not None:
            strokes_count = len(self.processor.current_strokes)
            self.lbl_stats.setText(f"Strokes: {strokes_count:,} | Points: {points:,}")

            h_img, w_img, ch = preview_img.shape
            bytes_per_line = ch * w_img
            
            qt_image = QImage(preview_img.data, w_img, h_img, bytes_per_line, QImage.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qt_image)
            
            self.lbl_preview.setPixmap(pixmap.scaled(self.lbl_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def force_focus(self):
        if self.isMinimized():
            self.showNormal()
        self.setWindowState((self.windowState() & ~Qt.WindowState.WindowMinimized) | Qt.WindowState.WindowActive)
        self.raise_()           
        self.activateWindow()

    def start_drawing(self):
        if not self.draw_area or not self.processor.current_strokes:
            return

        x, y, _, _ = self.draw_area
        strokes = self.processor.current_strokes

        self.enable_controls(False)
        self.btn_start.setText("DRAWING...")
        
        self.controller.start_drawing(strokes, x, y)

    def on_draw_complete(self):
        self.show_themed_messagebox("Success", "Drawing completed!", QMessageBox.Icon.Information)

    def on_draw_aborted(self):
        self.show_themed_messagebox("Aborted", "Drawing stopped by user.", QMessageBox.Icon.Warning)

    def on_draw_error(self, err_msg: str):
        self.show_themed_messagebox("Error", f"An error occurred:\n{err_msg}", QMessageBox.Icon.Critical)

    def reset_ui(self):
        self.enable_controls(True)
        self.btn_start.setText("3. START DRAWING")