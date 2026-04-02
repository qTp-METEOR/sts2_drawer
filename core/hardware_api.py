import ctypes
from typing import List, Tuple

# Win32 Constants
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

def right_click_down():
    """Simulates a hardware-level right mouse button press."""
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)

def right_click_up():
    """Simulates a hardware-level right mouse button release."""
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

def is_key_pressed(vk_code: int) -> bool:
    """Checks if a specific Virtual-Key is currently held down."""
    return bool(ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000)

def are_all_keys_pressed(vk_list: List[int]) -> bool:
    """Returns True only if EVERY key in the combination is currently pressed."""
    if not vk_list: 
        return False
    return all(is_key_pressed(vk) for vk in vk_list)

def get_virtual_screen_bounds() -> Tuple[int, int, int, int]:
    """Retrieves the raw hardware dimensions for the entire virtual desktop spanning all monitors."""
    x = ctypes.windll.user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    y = ctypes.windll.user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    w = ctypes.windll.user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    h = ctypes.windll.user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    return x, y, w, h