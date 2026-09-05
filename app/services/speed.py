# app/services/speed.py

import math
import time
from collections import defaultdict, deque


class SpeedAnalytics:
    """
    Speed Analytics Service

    Responsibilities
    ----------------
    • Per-track speed estimation
    • Rolling average speed
    • Fast mover detection
    • Slow mover detection

    This module performs NO orchestration.
    Fusion is responsible for coordinating updates.
    """

    FAST_THRESHOLD = 180.0      # pixels / second
    SLOW_THRESHOLD = 20.0       # pixels / second

    HISTORY_SIZE = 30

    def __init__(self):

        # track_id -> (cx, cy)
        self.last_position = {}

        # track_id -> timestamp
        self.last_timestamp = {}

        # latest instantaneous speed
        self.current_speed = {}

        # rolling history
        self.speed_history = defaultdict(
            lambda: deque(maxlen=self.HISTORY_SIZE)
        )

    # =====================================================
    # UPDATE
    # =====================================================
    def update(self, track_id, cx, cy):

        now = time.time()

        # First observation
        if track_id not in self.last_position:

            self.last_position[track_id] = (cx, cy)
            self.last_timestamp[track_id] = now
            self.current_speed[track_id] = 0.0

            return

        px, py = self.last_position[track_id]
        previous_time = self.last_timestamp[track_id]

        dt = now - previous_time

        # Prevent divide-by-zero
        if dt <= 0:
            return

        distance = math.hypot(
            cx - px,
            cy - py
        )

        speed = distance / dt

        self.current_speed[track_id] = speed

        self.speed_history[track_id].append(speed)

        self.last_position[track_id] = (cx, cy)
        self.last_timestamp[track_id] = now

    # =====================================================
    # TRACK SPEED
    # =====================================================
    def get_track_speed(self, track_id):

        history = self.speed_history.get(track_id)

        if not history:
            return 0.0

        return sum(history) / len(history)

    # =====================================================
    # SUMMARY
    # =====================================================
    def get_speed_summary(self):

        if not self.current_speed:

            return {
                "tracked_objects": 0,
                "average_speed": 0.0,
                "maximum_speed": 0.0,
                "fast_movers": 0,
                "slow_movers": 0
            }

        speeds = list(self.current_speed.values())

        fast = sum(
            s >= self.FAST_THRESHOLD
            for s in speeds
        )

        slow = sum(
            s <= self.SLOW_THRESHOLD
            for s in speeds
        )

        return {

            "tracked_objects": len(speeds),

            "average_speed": round(
                sum(speeds) / len(speeds),
                2
            ),

            "maximum_speed": round(
                max(speeds),
                2
            ),

            "fast_movers": fast,

            "slow_movers": slow
        }


speed = SpeedAnalytics()