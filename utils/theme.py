import ctypes
import logging

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

logger = logging.getLogger("AutoDrawer")

def is_theme_dark(theme_string: str) -> bool:
    """Resolves 'System Default' to the actual OS mode (Dark or Light)."""
    if theme_string == "System Default":
        scheme = QApplication.styleHints().colorScheme()
        return scheme == Qt.ColorScheme.Dark
    return theme_string == "Dark"

def apply_native_titlebar_theme(hwnd: int, is_dark: bool):
    """Uses Win32 DWM to force the window titlebar to dark/light mode natively."""
    try:
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20 # Windows 11 and Win 10 >= 1809
        value = ctypes.c_int(1 if is_dark else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 
            DWMWA_USE_IMMERSIVE_DARK_MODE, 
            ctypes.byref(value), 
            ctypes.sizeof(value)
        )
    except Exception as e:
        logger.warning(f"Could not set native titlebar theme: {e}")