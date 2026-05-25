import sys
from pathlib import Path

def get_resource_path(relative_path: str) -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    
    if meipass is not None:
        base_path = Path(meipass)
    else:
        base_path = Path(__file__).resolve().parents[2]
        
    return base_path / relative_path