import cv2
import numpy as np
from rembg import remove
from pathlib import Path
from typing import List, Tuple
from utils.logger import logger

class ImageProcessor:
    def __init__(self):
        self.original_image = None
        self.original_data = None
        self.processed_bg_image = None
        self.current_edges = None
        self.current_strokes = []

    def load_image(self, image_path: str) -> bool:
        path = Path(image_path)
        if not path.exists():
            logger.error(f"Image not found: {path}")
            return False
            
        with open(path, 'rb') as f:
            self.original_data = f.read()
            
        img_array = np.frombuffer(self.original_data, np.uint8)
        self.original_image = cv2.imdecode(img_array, cv2.IMREAD_UNCHANGED)
        
        self.processed_bg_image = None
        return self.original_image is not None

    def process_background(self, remove_bg: bool):
        if self.original_image is None or self.original_data is None:
            return

        if remove_bg:
            logger.info("Running AI background removal...")
            try:
                subject_data = remove(self.original_data)
                img_bgra = cv2.imdecode(np.frombuffer(subject_data, np.uint8), cv2.IMREAD_UNCHANGED)
                self.processed_bg_image = self._standardize_to_bgra(img_bgra)
            except Exception as e:
                logger.error(f"AI Background removal failed: {e}")
                logger.info("Falling back to original image.")
                self.processed_bg_image = self._standardize_to_bgra(self.original_image)
        else:
            logger.info("Skipping background removal.")
            self.processed_bg_image = self._standardize_to_bgra(self.original_image)
    
    def _standardize_to_bgra(self, img: np.ndarray) -> np.ndarray:
        """
        Forces any input image (1, 3, or 4 channels) into a standard 4-channel BGRA matrix.
        This prevents downstream channel-mismatch crashes.
        """
        if img is None:
            return None
            
        if len(img.shape) == 2:
            return cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
            
        elif len(img.shape) == 3 and img.shape[2] == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
            
        elif len(img.shape) == 3 and img.shape[2] == 4:
            return img.copy()
            
        else:
            logger.warning(f"Unexpected image shape: {img.shape}. Attempting default conversion.")
            return img.copy()

    def optimize_drawing_path(self, strokes: List[np.ndarray]) -> List[np.ndarray]:
        """
        Sorts strokes using a Nearest Neighbor approach to minimize mouse travel time.
        Also reverses strokes if starting from the end point is closer.
        """
        if not strokes:
            return []

        unvisited = strokes.copy()
        # Start with the stroke closest to the top-left corner (0,0)
        unvisited.sort(key=lambda s: np.linalg.norm(s[0] - np.array([0, 0])))
        
        optimized_strokes = [unvisited.pop(0)]

        while unvisited:
            # The physical location where the mouse just lifted up
            last_point = optimized_strokes[-1][-1] 
            
            best_idx = 0
            best_dist = float('inf')
            reverse_stroke = False
            
            for i, stroke in enumerate(unvisited):
                start_pt = stroke[0]
                end_pt = stroke[-1]
                
                dist_to_start = np.linalg.norm(last_point - start_pt)
                dist_to_end = np.linalg.norm(last_point - end_pt)
                
                if dist_to_start < best_dist:
                    best_dist = dist_to_start
                    best_idx = i
                    reverse_stroke = False
                    
                if dist_to_end < best_dist:
                    best_dist = dist_to_end
                    best_idx = i
                    reverse_stroke = True
                    
            next_stroke = unvisited.pop(best_idx)
            
            if reverse_stroke:
                # Flip the array so the bot draws it backwards to save travel time
                next_stroke = next_stroke[::-1] 
                
            optimized_strokes.append(next_stroke)
            
        return optimized_strokes

    def generate_preview(self, max_w: int, max_h: int, threshold1: int, threshold2: int, speed: float, line_color: Tuple[int, int, int] = (0, 0, 0)) -> Tuple[np.ndarray, int]:
        if self.processed_bg_image is None:
            return None, 0

        h, w = self.processed_bg_image.shape[:2]
        scaling_factor = min(max_w / w, max_h / h)
        new_size = (int(w * scaling_factor), int(h * scaling_factor))
        resized = cv2.resize(self.processed_bg_image, new_size, interpolation=cv2.INTER_AREA)
        
        gray = cv2.cvtColor(resized, cv2.COLOR_BGRA2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        self.current_edges = cv2.Canny(blurred, threshold1=threshold1, threshold2=threshold2)

        contours, _ = cv2.findContours(self.current_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        
        raw_strokes = []
        point_count = 0
        
        # Noise filter threshold based on image resolution
        min_contour_length = max(3.0, (new_size[0] * 0.005)) 
        
        for contour in contours:
            length = cv2.arcLength(contour, False)
            if length < min_contour_length:
                continue # Skip micro-noise

            epsilon = speed * length * 0.001
            simplified_stroke = cv2.approxPolyDP(contour, epsilon, False)
            pts = simplified_stroke.reshape(-1, 2)
            
            if len(pts) > 1:
                raw_strokes.append(pts)

        # Apply the TSP optimization
        self.current_strokes = self.optimize_drawing_path(raw_strokes)
        
        # Count points after optimization and filtering
        point_count = sum(len(stroke) for stroke in self.current_strokes)

        preview_image_bgra = np.zeros((new_size[1], new_size[0], 4), dtype=np.uint8)
        color_with_alpha = (*line_color, 255) 
        
        for stroke in self.current_strokes:
            cv2.polylines(preview_image_bgra, [stroke], isClosed=False, color=color_with_alpha, thickness=1, lineType=cv2.LINE_AA)

        preview_image_rgba = cv2.cvtColor(preview_image_bgra, cv2.COLOR_BGRA2RGBA)

        return preview_image_rgba, point_count