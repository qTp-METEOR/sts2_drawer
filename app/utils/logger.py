import sys
import logging
import os
from pathlib import Path
from types import TracebackType
from typing import Type, Optional
from logging.handlers import RotatingFileHandler
from PySide6.QtCore import QObject, Signal

class ExceptionSignaler(QObject):
    error_signal = Signal(str, str) 

signaler = ExceptionSignaler()
logger = logging.getLogger("app")

def get_log_file_path() -> Path:
    app_name = "SlayTheSpire2Drawer"
    local_app_data = os.getenv('LOCALAPPDATA')
    
    if local_app_data:
        base_dir = Path(local_app_data) / app_name
    else:
        base_dir = Path.home() / f".{app_name}"
    
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "app.log"

def setup_logger():
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(module)s:%(lineno)d | %(message)s')

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)
    logger.addHandler(console)

    log_path = get_log_file_path()
    file_out = RotatingFileHandler(
        log_path, 
        maxBytes=5*1024*1024, 
        backupCount=3, 
        encoding='utf-8'
    )
    file_out.setLevel(logging.DEBUG)
    file_out.setFormatter(formatter)
    logger.addHandler(file_out)

    def handle_exception(exc_type: Type[BaseException], exc_value: Exception, exc_traceback: Optional[TracebackType]):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.critical("Uncaught Exception", exc_info=(exc_type, exc_value, exc_traceback))
        signaler.error_signal.emit("Critical Error", str(exc_value))

    sys.excepthook = handle_exception
    
    logger.info(f"--- Logger Initialized at {log_path} ---")
    return logger
