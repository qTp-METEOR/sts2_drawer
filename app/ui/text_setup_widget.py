from typing import Any, Dict, Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QFontComboBox,
                               QSpinBox, QRadioButton, QButtonGroup, QHBoxLayout,
                               QLabel, QGroupBox)
from PySide6.QtGui import QFont
from PySide6.QtCore import Signal

class TextModeWidget(QWidget):
    settings_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        input_group = QGroupBox("Text Input")
        input_layout = QVBoxLayout(input_group)
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Enter text to draw...")
        self.text_input.textChanged.connect(self.settings_changed.emit)
        input_layout.addWidget(self.text_input)
        layout.addWidget(input_group, stretch=1)

        font_group = QGroupBox("Font Settings")
        font_layout = QVBoxLayout(font_group)

        row1 = QHBoxLayout()
        self.font_combo = QFontComboBox()
        self.font_combo.setFontFilters(QFontComboBox.FontFilter.ScalableFonts)
        
        def on_font_changed(font: QFont):
            self.settings_changed.emit()
            
        self.font_combo.currentFontChanged.connect(on_font_changed)
        
        self.size_spin = QSpinBox()
        self.size_spin.setRange(10, 1000)
        self.size_spin.setValue(80)
        self.size_spin.setSuffix(" pt")
        self.size_spin.setMinimumWidth(85)
        
        def on_size_changed(val: int):
            self.settings_changed.emit()
            
        self.size_spin.valueChanged.connect(on_size_changed) 
        
        row1.addWidget(QLabel("Font:"))
        row1.addWidget(self.font_combo, stretch=1)
        row1.addWidget(self.size_spin)
        font_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Alignment:"))
        self.align_group = QButtonGroup(self)
        
        def on_align_toggled(checked: bool):
            self.settings_changed.emit()
        
        for align in ["Left", "Center", "Right"]:
            btn = QRadioButton(align)
            if align == "Center":
                btn.setChecked(True)
            self.align_group.addButton(btn)
            row2.addWidget(btn)
            btn.toggled.connect(on_align_toggled)
            
        row2.addStretch()
        font_layout.addLayout(row2)
        
        layout.addWidget(font_group)


    def get_settings(self) -> Dict[str, Any]:
        """Helper method for MainWindow to easily grab all current values."""
        checked_button = self.align_group.checkedButton()
        alignment_text = checked_button.text() if checked_button else "Center"
        
        return {
            "text": self.text_input.toPlainText(),
            "font_family": self.font_combo.currentFont().family(),
            "font_size": self.size_spin.value(),
            "alignment": alignment_text
        }
