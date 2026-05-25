from typing import Any, Dict, Optional, Union
from PySide6.QtWidgets import (QLabel, QWidget, QVBoxLayout, QPushButton, QCheckBox,
                               QGroupBox, QFormLayout, QSlider, QSpinBox,
                               QDoubleSpinBox, QHBoxLayout, QSizePolicy)
from PySide6.QtCore import Qt, Signal

class ImageModeWidget(QWidget):
    load_requested = Signal()
    bg_toggled = Signal(bool)
    settings_changed = Signal()
    delay_changed = Signal(int)

    def __init__(self, initial_delay: int = 10, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.initial_delay = initial_delay
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.btn_load_image = QPushButton("Load Image")
        self.btn_load_image.clicked.connect(self.load_requested.emit)
        layout.addWidget(self.btn_load_image)

        settings_group = QGroupBox("Processing Settings")
        form_layout = QFormLayout(settings_group)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.chk_remove_bg = QCheckBox("AI Background Removal")
        self.chk_remove_bg.setChecked(True)
        self.chk_remove_bg.setEnabled(False)
        
        def on_bg_toggled(state: int):
            self.bg_toggled.emit(self.chk_remove_bg.isChecked())
            
        self.chk_remove_bg.stateChanged.connect(on_bg_toggled)
        form_layout.addRow("", self.chk_remove_bg)

        canny_min_tip = "Controls the sensitivity for subtle details. Lower values pick up more faint textures and noise, while higher values ignore them."
        self.slider_thresh1, self.spin_thresh1 = self.create_setting_row(
            form_layout, "Canny Min:", 0, 255, 50, tooltip=canny_min_tip
        )

        canny_max_tip = "Defines what counts as a 'strong' edge. Lower values force the algorithm to find more edges overall. Higher values restrict it to only the sharpest, most obvious outlines."
        self.slider_thresh2, self.spin_thresh2 = self.create_setting_row(
            form_layout, "Canny Max:", 0, 255, 100, tooltip=canny_max_tip
        )
        
        self.slider_speed, self.spin_speed = self.create_setting_row(
            form_layout, "Speed/Detail:", 1, 100, 10, is_float=True
        )
        
        self.slider_delay, self.spin_delay = self.create_setting_row(
            form_layout, "Click Delay (ms):", 1, 20, self.initial_delay
        )
        
        def on_delay_changed(val: int):
            self.delay_changed.emit(val)
            
        self.spin_delay.valueChanged.connect(on_delay_changed)

        self.btn_reset = QPushButton("↺ Reset Defaults")
        self.btn_reset.setEnabled(False)
        self.btn_reset.clicked.connect(self.reset_to_defaults)
        form_layout.addRow("", self.btn_reset)

        layout.addWidget(settings_group)
        layout.addStretch()

    def create_setting_row(self, layout: QFormLayout, label_name: str, min_val: int, max_val: int, default_val: int, is_float: bool = False, tooltip: str = "") -> tuple[QSlider, Union[QDoubleSpinBox, QSpinBox]]:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        slider.setEnabled(False)

        spin_box: Union[QDoubleSpinBox, QSpinBox]
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

        if tooltip:
            slider.setToolTip(tooltip)
            spin_box.setToolTip(tooltip)

        def on_slider_changed(val: int):
            spin_box.blockSignals(True) 
            if isinstance(spin_box, QDoubleSpinBox):
                spin_box.setValue(val / 10.0)
            else:
                spin_box.setValue(val)
            spin_box.blockSignals(False)
            self.settings_changed.emit()

        def on_spin_changed(val: Union[float, int]):
            slider.blockSignals(True) 
            if isinstance(spin_box, QDoubleSpinBox):
                slider.setValue(int(val * 10))
            else:
                slider.setValue(int(val))
            slider.blockSignals(False)
            self.settings_changed.emit()

        slider.valueChanged.connect(on_slider_changed)
        spin_box.valueChanged.connect(on_spin_changed)

        h_layout = QHBoxLayout()
        h_layout.addWidget(slider)
        h_layout.addWidget(spin_box)
        h_layout.setContentsMargins(0, 0, 0, 0)
        
        display_label = f"{label_name} ⓘ" if tooltip else label_name
        label = QLabel(display_label)
        
        if tooltip:
            label.setToolTip(tooltip)
            
        layout.addRow(label, h_layout)
        
        return slider, spin_box

    def enable_controls(self, state: bool):
        """Called by MainWindow to unlock the UI once an image is successfully loaded."""
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

    def set_load_button_text(self, text: str):
        self.btn_load_image.setText(text)

    def reset_to_defaults(self):
        self.slider_thresh1.setValue(50)
        self.slider_thresh2.setValue(100)
        self.slider_speed.setValue(10)
        if not self.chk_remove_bg.isChecked():
            self.chk_remove_bg.setChecked(True)
        else:
            self.settings_changed.emit()

    def get_settings(self) -> Dict[str, Any]:
        """Helper method for MainWindow to easily grab all current values."""
        return {
            "remove_bg": self.chk_remove_bg.isChecked(),
            "thresh1": self.slider_thresh1.value(),
            "thresh2": self.slider_thresh2.value(),
            "speed": self.slider_speed.value() / 10.0
        }