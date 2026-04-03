import os
from typing import Optional

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTabWidget, QWidget, 
                               QFormLayout, QComboBox, QTextEdit, QLabel, 
                               QPushButton)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QKeySequence, QMouseEvent

from utils.theme import is_theme_dark, apply_native_titlebar_theme
from core.config import config

class KeybindRecorder(QPushButton):
    """Custom button that listens for both key presses AND mouse clicks."""
    key_changed = Signal(str)

    def __init__(self, current_key: str):
        super().__init__(current_key)
        self.setCheckable(True)
        self.toggled.connect(self.on_toggle)

    def on_toggle(self, checked: bool):
        if checked:
            self.setText("Press combination...")
            self.setStyleSheet("background-color: #aa8800; color: white;") 
        else:
            self.setStyleSheet("") 

    def keyPressEvent(self, event: QKeyEvent):
        if not self.isChecked():
            super().keyPressEvent(event)
            return

        key = event.key()
        if key in (Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return

        combo = event.keyCombination()
        sequence = QKeySequence(combo).toString()
        
        self.setText(sequence)
        self.setChecked(False)
        self.key_changed.emit(sequence)

    def mousePressEvent(self, event: QMouseEvent):
        if not self.isChecked():
            super().mousePressEvent(event)
            return

        btn = event.button()
        btn_str = ""
        
        if btn == Qt.MouseButton.LeftButton: btn_str = "Mouse Left"
        elif btn == Qt.MouseButton.RightButton: btn_str = "Mouse Right"
        elif btn == Qt.MouseButton.MiddleButton: btn_str = "Mouse Middle"
        elif btn in (Qt.MouseButton.BackButton, Qt.MouseButton.ExtraButton1): btn_str = "Mouse X1"
        elif btn in (Qt.MouseButton.ForwardButton, Qt.MouseButton.ExtraButton2): btn_str = "Mouse X2"
        
        if btn_str:
            modifiers = event.modifiers()
            prefix = ""
            if modifiers & Qt.KeyboardModifier.ControlModifier: prefix += "Ctrl+"
            if modifiers & Qt.KeyboardModifier.ShiftModifier: prefix += "Shift+"
            if modifiers & Qt.KeyboardModifier.AltModifier: prefix += "Alt+"
            
            sequence = prefix + btn_str
            self.setText(sequence)
            self.setChecked(False)
            self.key_changed.emit(sequence)
        else:
            super().mousePressEvent(event)

class SettingsDialog(QDialog):
    theme_changed = Signal(str)

    def __init__(self, current_theme: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("⚙ Settings")
        self.setMinimumSize(500, 400)
        self.current_theme: str = current_theme

        self.setup_ui()
        self.apply_titlebar_theme() 

    def apply_titlebar_theme(self):
        is_dark = is_theme_dark(self.current_theme)
        apply_native_titlebar_theme(int(self.winId()), is_dark)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        tab_general = QWidget()
        form_layout = QFormLayout(tab_general)
        
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["System Default", "Dark", "Light"])
        self.combo_theme.setCurrentText(self.current_theme)
        self.combo_theme.currentTextChanged.connect(self.on_theme_changed)
        
        form_layout.addRow("Application Theme:", self.combo_theme)
        tabs.addTab(tab_general, "General")

        tab_keybinds = QWidget()
        key_layout = QFormLayout(tab_keybinds)
        
        self.btn_pause_bind = KeybindRecorder(config.pause_key)
        self.btn_abort_bind = KeybindRecorder(config.abort_key)
        
        self.btn_pause_bind.key_changed.connect(self.save_keybinds)
        self.btn_abort_bind.key_changed.connect(self.save_keybinds)
        
        key_layout.addRow("Pause / Resume:", self.btn_pause_bind)
        key_layout.addRow("Emergency Abort:", self.btn_abort_bind)
        
        btn_reset_binds = QPushButton("↺ Reset to Defaults")
        btn_reset_binds.clicked.connect(self.reset_keybinds)
        key_layout.addRow("", btn_reset_binds)
        
        tabs.addTab(tab_keybinds, "Keybinds")

        tab_logs = QWidget()
        log_layout = QVBoxLayout(tab_logs)
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.log_viewer.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        
        btn_refresh_logs = QPushButton("↻ Refresh Logs")
        btn_refresh_logs.clicked.connect(self.load_logs)
        
        log_layout.addWidget(btn_refresh_logs)
        log_layout.addWidget(self.log_viewer)
        tabs.addTab(tab_logs, "System Logs")
        self.load_logs()

        tab_about = QWidget()
        about_layout = QVBoxLayout(tab_about)
        about_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title = QLabel("<h2>StS2 Drawer</h2>")
        lbl_version = QLabel("<b>Version:</b> 1.0.0")
        lbl_github = QLabel('<a href="https://github.com/qTp-METEOR/sts2_drawer">View Source on GitHub</a>')
        lbl_github.setOpenExternalLinks(True)
        lbl_credits = QLabel("Built with PySide6, OpenCV, and Rembg.")
        lbl_credits.setStyleSheet("color: #888; font-style: italic;")

        about_layout.addWidget(lbl_title)
        about_layout.addWidget(lbl_version)
        about_layout.addWidget(lbl_github)
        about_layout.addSpacing(20)
        about_layout.addWidget(lbl_credits)
        tabs.addTab(tab_about, "About")

        layout.addWidget(tabs)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

    def reset_keybinds(self):
        self.btn_pause_bind.setText("P")
        self.btn_abort_bind.setText("Esc")
        config.pause_key = "P"
        config.abort_key = "Esc"

    def save_keybinds(self):
        pause = self.btn_pause_bind.text()
        abort = self.btn_abort_bind.text()
        
        if pause == abort:
            self.reset_keybinds()
        else:
            config.pause_key = pause
            config.abort_key = abort

    def on_theme_changed(self, new_theme: str):
        self.current_theme = new_theme
        self.apply_titlebar_theme() 
        self.theme_changed.emit(new_theme)

    def load_logs(self):
        log_path = "app.log"
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-100:]
                self.log_viewer.setPlainText("".join(lines))
                self.log_viewer.verticalScrollBar().setValue(self.log_viewer.verticalScrollBar().maximum())