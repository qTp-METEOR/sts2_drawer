import time
from typing import List
import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QCursor
from utils.logger import logger
from core import hardware_api

class DrawingWorker(QThread):
    progress = Signal(int, int, int, str)
    draw_completed = Signal()
    error = Signal(str)
    aborted = Signal()
    status_changed = Signal(bool)

    def __init__(self, strokes: List[np.ndarray], offset_x: int, offset_y: int, abort_vks: List[int], pause_vks: List[int], delay_ms: int = 2):
        super().__init__()
        self.strokes = strokes
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.abort_vks = abort_vks
        self.pause_vks = pause_vks
        
        self._is_running = True
        self._is_paused = False
        self._last_p_state = False

        self.total_points = sum(len(stroke) for stroke in strokes)
        self.points_drawn = 0
        self.active_time_elapsed = 0.0

        self.point_delay = max(0.001, delay_ms / 1000.0)
        self.click_delay = self.point_delay * 5

    def set_pos(self, x: int, y: int):
        QCursor.setPos(int(self.offset_x + x), int(self.offset_y + y))

    def check_input(self):
        # Abort Check
        if hardware_api.are_all_keys_pressed(self.abort_vks):
            self._is_running = False
            return

        # Pause/Resume Check
        current_p_state = hardware_api.are_all_keys_pressed(self.pause_vks)
        if current_p_state and not self._last_p_state:
            self._is_paused = not self._is_paused
            self.status_changed.emit(self._is_paused)
            if self._is_paused:
                hardware_api.right_click_up()

        self._last_p_state = current_p_state

    def run(self):
        try:
            total_strokes = len(self.strokes)
            time.sleep(0.5) 
            last_timestamp = time.time()

            for i, stroke in enumerate(self.strokes):
                self.check_input()
                if not self._is_running:
                    self.aborted.emit()
                    return

                while self._is_paused and self._is_running:
                    time.sleep(0.05)
                    self.check_input()
                    last_timestamp = time.time()

                if not self._is_running:
                    self.aborted.emit()
                    return

                first_point = stroke[0]
                self.set_pos(*first_point)
                time.sleep(self.click_delay)
                hardware_api.right_click_down()
                time.sleep(self.point_delay)

                for point in stroke[1:]:
                    self.check_input()
                    
                    while self._is_paused and self._is_running:
                        time.sleep(self.point_delay)
                        self.check_input()
                        last_timestamp = time.time()

                    if not self._is_running:
                        hardware_api.right_click_up()
                        self.aborted.emit()
                        return

                    self.set_pos(*point)
                    time.sleep(self.point_delay)

                hardware_api.right_click_up()

                self.points_drawn += len(stroke)
                current = i + 1
                now = time.time()
                self.active_time_elapsed += (now - last_timestamp)
                last_timestamp = now

                percentage = int((self.points_drawn / self.total_points) * 100)
                
                if self.active_time_elapsed > 1.0 and self.points_drawn > 0:
                    points_per_second = self.points_drawn / self.active_time_elapsed
                    points_left = self.total_points - self.points_drawn
                    if points_per_second > 0:
                        eta_seconds = points_left / points_per_second
                        eta_mins, eta_secs = divmod(int(eta_seconds), 60)
                        eta_str = f"{eta_mins}m {eta_secs:02d}s"
                    else:
                        eta_str = "Calculating..."
                else:
                    eta_str = "Calculating..."

                self.progress.emit(current, total_strokes, percentage, eta_str)

            self.draw_completed.emit()
        except Exception as e:
            logger.exception("Worker run loop failed.")
            self.error.emit(str(e))