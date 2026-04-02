import ctypes

def _build_vk_map():
    """Dynamically builds the Virtual-Key dictionary for comprehensive hardware support."""
    vk_map = {
        "Esc": 0x1B, "Space": 0x20, "Enter": 0x0D, "Return": 0x0D, "Tab": 0x09, "Backspace": 0x08,
        "Up": 0x26, "Down": 0x28, "Left": 0x25, "Right": 0x27,
        "Ctrl": 0x11, "Shift": 0x10, "Alt": 0x12, "Meta": 0x5B,
        
        # Mouse buttons explicitly mapped
        "Mouse Left": 0x01, "Mouse Right": 0x02, "Mouse Middle": 0x04,
        "Mouse X1": 0x05, "Mouse X2": 0x06, "Mouse Back": 0x05, "Mouse Forward": 0x06,
        
        # Numpad explicitly mapped
        "Num 0": 0x60, "Num 1": 0x61, "Num 2": 0x62, "Num 3": 0x63, "Num 4": 0x64,
        "Num 5": 0x65, "Num 6": 0x66, "Num 7": 0x67, "Num 8": 0x68, "Num 9": 0x69,
        "Num *": 0x6A, "Num +": 0x6B, "Num -": 0x6D, "Num .": 0x6E, "Num /": 0x6F,
    }
    
    # Dynamically map F1 through F24
    for i in range(1, 25):
        vk_map[f"F{i}"] = 0x6F + i
        
    # Dynamically map A-Z using the OS directly
    for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        vk_map[char] = ctypes.windll.user32.VkKeyScanW(ord(char)) & 0xFF
        
    # Dynamically map 0-9 (Top Row)
    for i in range(10):
        vk_map[str(i)] = 0x30 + i
        
    return vk_map

VK_MAP = _build_vk_map()

def parse_keybind_string(bind_str: str) -> list[int]:
    """Converts a formatted string like 'Ctrl+Mouse X1' to a list of Win32 hex codes."""
    keys = bind_str.split('+')
    return [VK_MAP.get(k.strip(), 0) for k in keys if k.strip() in VK_MAP]