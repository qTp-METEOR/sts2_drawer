from PySide6.QtCore import QSettings

class ConfigManager:
    """Single source of truth for application settings."""
    def __init__(self):
        self._settings = QSettings("AutoDrawerOrg", "AutoDrawer")

    @property
    def theme(self) -> str:
        return str(self._settings.value("theme", "System Default"))

    @theme.setter
    def theme(self, value: str):
        self._settings.setValue("theme", value)

    @property
    def pause_key(self) -> str:
        return str(self._settings.value("pause_key", "P"))
    
    @property
    def drawing_delay(self) -> int:
        """Delay between points in milliseconds. Default 2ms."""
        return int(self._settings.value("drawing_delay", 2))

    @drawing_delay.setter
    def drawing_delay(self, value: int):
        self._settings.setValue("drawing_delay", value)

    @pause_key.setter
    def pause_key(self, value: str):
        self._settings.setValue("pause_key", value)

    @property
    def abort_key(self) -> str:
        return str(self._settings.value("abort_key", "Esc"))

    @abort_key.setter
    def abort_key(self, value: str):
        self._settings.setValue("abort_key", value)

# Global instance
config = ConfigManager()