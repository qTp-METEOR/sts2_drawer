import logging
from typing import Any, List, Tuple, cast
from numpy.typing import NDArray
import numpy as np

from PySide6.QtGui import QFont, QFontMetrics, QPainterPath

logger = logging.getLogger(__name__)


class TextProcessor:
    def __init__(self):
        self.current_strokes: List[NDArray[np.int32]] = []

    def _wrap_text(
        self, text: str, metrics: QFontMetrics, max_width: int
    ) -> List[str]:
        """Calculates line breaks automatically based on font metrics and maximum pixel width.
        Respects hard line breaks entered by the user.
        """
        wrapped_lines: List[str] = []
        paragraphs = text.split("\n")

        for paragraph in paragraphs:
            if not paragraph.strip():
                wrapped_lines.append("")
                continue

            words = paragraph.split(" ")
            if not words:
                continue

            current_line = words[0]

            for word in words[1:]:
                test_line = current_line + " " + word
                if metrics.horizontalAdvance(test_line) <= max_width:
                    current_line = test_line
                else:
                    wrapped_lines.append(current_line)
                    current_line = word

            wrapped_lines.append(current_line)

        return wrapped_lines

    def generate_strokes(
        self,
        text: str,
        font_family: str,
        font_size: int,
        area_w: int,
        area_h: int,
        alignment: str = "Center",
    ) -> Tuple[List[NDArray[np.int32]], int]:
        """Converts text into a list of drawable numpy arrays, applying auto-wrap."""
        if not text.strip():
            self.current_strokes = []
            return [], 0

        path = QPainterPath()
        font = QFont(font_family, font_size)
        metrics = QFontMetrics(font)

        lines = self._wrap_text(text, metrics, area_w)

        line_spacing = metrics.lineSpacing()
        total_text_height = line_spacing * len(lines)

        if area_h > total_text_height:
            current_y = (area_h - total_text_height) // 2 + metrics.ascent()
        else:
            current_y = metrics.ascent()

        for line in lines:
            if not line.strip():
                current_y += line_spacing
                continue

            text_width = metrics.horizontalAdvance(line)

            if alignment == "Center":
                x_offset = (area_w - text_width) / 2
            elif alignment == "Right":
                x_offset = area_w - text_width
            else:
                x_offset = 0

            path.addText(x_offset, current_y, font, line)
            current_y += line_spacing

        raw_strokes: List[NDArray[np.int32]] = []
        for polygon in path.toSubpathPolygons():
            # Cast polygon to Any to bypass broken PySide6 __iter__ type stubs
            pts = np.array([[p.x(), p.y()] for p in cast(Any, polygon)], dtype=np.int32)
            if len(pts) > 1:
                densified_pts = self._interpolate_stroke(pts, max_step=1.5)
                raw_strokes.append(densified_pts)
            
        self.current_strokes = self.optimize_drawing_path(raw_strokes)
        point_count = sum(len(s) for s in self.current_strokes)

        return self.current_strokes, point_count

    def optimize_drawing_path(
        self, strokes: List[NDArray[Any]]
    ) -> List[NDArray[Any]]:
        """Sorts strokes to minimize travel distance between them."""
        if not strokes:
            return []

        unvisited = list(strokes)
        unvisited.sort(
            key=lambda s: float(np.linalg.norm(s[0] - np.array([0, 0])))
        )

        optimized_strokes: List[NDArray[Any]] = [unvisited.pop(0)]

        while unvisited:
            last_point = optimized_strokes[-1][-1]
            best_idx, best_dist, reverse_stroke = 0, float("inf"), False

            for i, stroke in enumerate(unvisited):
                dist_start = float(np.linalg.norm(last_point - stroke[0]))
                dist_end = float(np.linalg.norm(last_point - stroke[-1]))

                if dist_start < best_dist:
                    best_dist, best_idx, reverse_stroke = dist_start, i, False
                if dist_end < best_dist:
                    best_dist, best_idx, reverse_stroke = dist_end, i, True

            next_stroke = unvisited.pop(best_idx)
            optimized_strokes.append(
                next_stroke[::-1] if reverse_stroke else next_stroke
            )

        return optimized_strokes
    
    def _interpolate_stroke(self, points: NDArray[np.int32], max_step: float = 2.0) -> NDArray[np.int32]:
        """Fills in gaps between distant vertices to ensure a uniform point density."""
        interpolated: List[NDArray[Any]] = []
        
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            interpolated.append(p1)
            
            dist = np.linalg.norm(p2 - p1)
            if dist > max_step:
                num_steps = int(np.ceil(dist / max_step))
                for step in range(1, num_steps):
                    t = step / num_steps
                    interp_pt = p1 + (p2 - p1) * t
                    interpolated.append(interp_pt)
                    
        interpolated.append(points[-1])
        return np.array(interpolated, dtype=np.int32)