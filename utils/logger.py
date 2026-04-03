import sys
import logging
from types import TracebackType
from typing import Type, Optional
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import QObject, Signal

class ExceptionSignaler(QObject):
    """Safely bridges backend/thread exceptions to the main Qt GUI thread."""
    error_signal = Signal(str, str) 

signaler = ExceptionSignaler()
logger = logging.getLogger("AutoDrawer")

def setup_logger():
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(module)s:%(lineno)d | %(message)s')

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)

    file_out = RotatingFileHandler("app.log", maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    file_out.setLevel(logging.DEBUG)
    file_out.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file_out)

    def handle_exception(exc_type: Type[BaseException], exc_value: Exception, exc_traceback: Optional[TracebackType]):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.critical("Uncaught Exception", exc_info=(exc_type, exc_value, exc_traceback))
        signaler.error_signal.emit("Critical Error", str(exc_value))

    sys.excepthook = handle_exception
    
    logger.info("--- Logger Initialized ---")
    return logger