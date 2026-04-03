from pathlib import Path
from typing import List, Optional, Tuple, cast, Any

import cv2
import numpy as np
from numpy.typing import NDArray
from rembg import remove # type: ignore

from utils.logger import logger

class ImageProcessor:
    def __init__(self) -> None:
        self.original_image: Optional[NDArray[np.uint8]] = None
        self.original_data: Optional[bytes] = None
        self.processed_bg_image: Optional[NDArray[np.uint8]] = None
        self.current_edges: Optional[NDArray[np.uint8]] = None
        self.current_strokes: List[NDArray[np.int32]] = []

    def load_image(self, image_path: str) -> bool:
        path = Path(image_path)
        if not path.exists():
            logger.error(f"Image not found: {path}")
            return False
            
        with open(path, 'rb') as f:
            self.original_data = f.read()
            
        img_array = np.frombuffer(self.original_data, np.uint8)
        decoded = cv2.imdecode(img_array, cv2.IMREAD_UNCHANGED)
        self.original_image = cast(Optional[NDArray[np.uint8]], decoded)
        
        self.processed_bg_image = None
        return self.original_image is not None

    def process_background(self, remove_bg: bool) -> None:
        if self.original_image is None or self.original_data is None:
            return

        if remove_bg:
            logger.info("Running AI background removal...")
            try:
                subject_data = cast(bytes, remove(self.original_data))
                decoded_bg = cv2.imdecode(np.frombuffer(subject_data, np.uint8), cv2.IMREAD_UNCHANGED)
                img_bgra = cast(NDArray[np.uint8], decoded_bg)
                self.processed_bg_image = self._standardize_to_bgra(img_bgra)
            except Exception as e:
                logger.error(f"AI Background removal failed: {e}")
                logger.info("Falling back to original image.")
                self.processed_bg_image = self._standardize_to_bgra(self.original_image)
        else:
            logger.info("Skipping background removal.")
            self.processed_bg_image = self._standardize_to_bgra(self.original_image)
    
    def _standardize_to_bgra(self, img: Optional[NDArray[np.uint8]]) -> Optional[NDArray[np.uint8]]:
        if img is None:
            return None
            
        shape = img.shape
        if len(shape) == 2:
            result = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
        elif len(shape) == 3 and shape[2] == 3:
            result = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        elif len(shape) == 3 and shape[2] == 4:
            result = img.copy()
        else:
            logger.warning(f"Unexpected image shape: {shape}. Attempting default conversion.")
            result = img.copy()
            
        return cast(NDArray[np.uint8], result)

    def optimize_drawing_path(self, strokes: List[NDArray[Any]]) -> List[NDArray[Any]]:
        if not strokes:
            return []

        unvisited = list(strokes)
        unvisited.sort(key=lambda s: float(np.linalg.norm(s[0] - np.array([0, 0]))))
        
        optimized_strokes: List[NDArray[Any]] = [unvisited.pop(0)]

        while unvisited:
            last_point = optimized_strokes[-1][-1] 
            best_idx, best_dist, reverse_stroke = 0, float('inf'), False
            
            for i, stroke in enumerate(unvisited):
                dist_start = float(np.linalg.norm(last_point - stroke[0]))
                dist_end = float(np.linalg.norm(last_point - stroke[-1]))
                
                if dist_start < best_dist:
                    best_dist, best_idx, reverse_stroke = dist_start, i, False
                if dist_end < best_dist:
                    best_dist, best_idx, reverse_stroke = dist_end, i, True
                    
            next_stroke = unvisited.pop(best_idx)
            optimized_strokes.append(next_stroke[::-1] if reverse_stroke else next_stroke)
            
        return optimized_strokes

    def generate_preview(
        self, max_w: int, max_h: int, threshold1: int, threshold2: int, speed: float, 
        line_color: Tuple[int, int, int] = (0, 0, 0)
    ) -> Tuple[Optional[NDArray[np.uint8]], int]:
        if self.processed_bg_image is None:
            return None, 0

        h, w = self.processed_bg_image.shape[:2]
        scaling_factor = min(max_w / w, max_h / h)
        new_size = (int(w * scaling_factor), int(h * scaling_factor))
        
        resized = cv2.resize(self.processed_bg_image, new_size, interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGRA2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        edges = cv2.Canny(blurred, threshold1=threshold1, threshold2=threshold2)
        self.current_edges = cast(NDArray[np.uint8], edges)

        contours, _ = cv2.findContours(self.current_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        
        raw_strokes: List[NDArray[Any]] = []
        min_len = max(3.0, (new_size[0] * 0.005)) 
        
        for contour in contours:
            length = float(cv2.arcLength(contour, False))
            if length < min_len: continue

            simplified = cv2.approxPolyDP(contour, speed * length * 0.001, False)
            pts = simplified.reshape(-1, 2)
            if len(pts) > 1:
                raw_strokes.append(pts)

        self.current_strokes = cast(List[NDArray[np.int32]], self.optimize_drawing_path(raw_strokes))
        point_count = sum(len(s) for s in self.current_strokes)

        preview = np.zeros((new_size[1], new_size[0], 4), dtype=np.uint8)
        color_alpha = (*line_color, 255) 
        
        for stroke in self.current_strokes:
            cv2.polylines(preview, [stroke], isClosed=False, color=color_alpha, thickness=1, lineType=cv2.LINE_AA)

        final_preview = cv2.cvtColor(preview, cv2.COLOR_BGRA2RGBA)
        
        return cast(NDArray[np.uint8], final_preview), point_count