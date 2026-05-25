import sys
from app.utils.logger import setup_logger
from app.core.bootstrap import AppOrchestrator

def main() -> None:
    setup_logger()
    orchestrator = AppOrchestrator()
    sys.exit(orchestrator.app.exec())

if __name__ == "__main__":
    main()