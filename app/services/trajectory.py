# app/services/trajectory.py

import math
import time
from collections import defaultdict, deque


class TrajectoryAnalytics:
    """
    Trajectory Analytics Service

    Responsibilities
    ----------------
    • Store recent trajectory per track
    • Compute total travel distance
    • Estimate movement direction
    • Track direction history
    • Track direction changes
    • Compute dominant direction
    • Provide trajectory summaries

    NOTE:
    This module performs NO orchestration.
    Fusion coordinates all analytics services.
    """

    PATH_HISTORY = 100

    def __init__(self):

        # track_id -> deque[(cx, cy)]
        self.paths = defaultdict(
            lambda: deque(maxlen=self.PATH_HISTORY)
        )

        # track_id -> cumulative travel distance
        self.total_distance = defaultdict(float)

        # track_id -> first seen timestamp
        self.first_seen = {}

        # track_id -> last seen timestamp
        self.last_seen = {}

        # Active tracks for current frame
        self.current_active = set()

        # =====================================
        # Direction Analytics
        # =====================================

        # track_id -> direction history
        self.direction_history = defaultdict(
            lambda: deque(maxlen=50)
        )

        # track_id -> number of direction changes
        self.direction_changes = defaultdict(int)

    # =====================================
    # FRAME FINALIZATION
    # =====================================
    def finalize_frame(self, active_tracks):

        self.current_active = set(active_tracks)

    # =====================================================
    # UPDATE
    # =====================================================
    def update(self, track_id, cx, cy):

        now = time.time()

        if track_id not in self.first_seen:
            self.first_seen[track_id] = now

        self.last_seen[track_id] = now

        path = self.paths[track_id]

        # Compute travelled distance
        if len(path) > 0:

            px, py = path[-1]

            distance = math.hypot(
                cx - px,
                cy - py
            )

            self.total_distance[track_id] += distance

        path.append((cx, cy))

        # Update direction analytics
        self.update_direction_history(track_id)

    # =====================================================
    # TRACK PATH
    # =====================================================
    def get_track_path(self, track_id):

        return list(
            self.paths.get(track_id, [])
        )

    # =====================================================
    # TRACK DISTANCE
    # =====================================================
    def get_track_distance(self, track_id):

        return round(
            self.total_distance.get(track_id, 0.0),
            2
        )

    # =====================================================
    # MOVEMENT DIRECTION
    # =====================================================
    def get_track_direction(self, track_id):

        path = self.paths.get(track_id)

        if path is None or len(path) < 2:
            return "STATIONARY"

        x1, y1 = path[-2]
        x2, y2 = path[-1]

        dx = x2 - x1
        dy = y2 - y1

        # Ignore tiny movements
        if abs(dx) < 2 and abs(dy) < 2:
            return "STATIONARY"

        angle = math.degrees(
            math.atan2(-dy, dx)
        )

        angle %= 360

        directions = [
            "EAST",
            "NORTH-EAST",
            "NORTH",
            "NORTH-WEST",
            "WEST",
            "SOUTH-WEST",
            "SOUTH",
            "SOUTH-EAST"
        ]

        index = int(
            ((angle + 22.5) % 360) / 45
        )

        return directions[index]

    # =====================================================
    # RECORD DIRECTION HISTORY
    # =====================================================
    def update_direction_history(self, track_id):

        direction = self.get_track_direction(track_id)

        history = self.direction_history[track_id]

        if history:

            previous = history[-1]

            if (
                direction != previous
                and direction != "STATIONARY"
                and previous != "STATIONARY"
            ):
                self.direction_changes[track_id] += 1

        history.append(direction)

    # =====================================================
    # DOMINANT DIRECTION
    # =====================================================
    def get_dominant_direction(self, track_id):

        history = self.direction_history.get(track_id)

        if not history:
            return "UNKNOWN"

        counts = {}

        for direction in history:

            if direction == "STATIONARY":
                continue

            counts[direction] = (
                counts.get(direction, 0) + 1
            )

        if not counts:
            return "STATIONARY"

        return max(
            counts,
            key=counts.get
        )

    # =====================================================
    # DIRECTION CHANGES
    # =====================================================
    def get_direction_changes(self, track_id):

        return self.direction_changes.get(
            track_id,
            0
        )

    # =====================================================
    # TRACK SUMMARY
    # =====================================================
    def get_track_summary(self, track_id):

        first_seen = self.first_seen.get(track_id)
        last_seen = self.last_seen.get(track_id)

        tracking_duration = 0.0

        if first_seen is not None and last_seen is not None:
            tracking_duration = round(
                last_seen - first_seen,
                2
            )

        return {

            "track_id": track_id,

            "trajectory_points": len(
                self.paths.get(track_id, [])
            ),

            "distance_travelled": self.get_track_distance(
                track_id
            ),

            "direction": self.get_track_direction(
                track_id
            ),

            "dominant_direction": self.get_dominant_direction(
                track_id
            ),

            "direction_changes": self.direction_changes.get(
                track_id,
                0
            ),

            "tracking_duration": tracking_duration,

            "first_seen": first_seen,

            "last_seen": last_seen
        }

    # =====================================================
    # GLOBAL TRAJECTORY SUMMARY
    # =====================================================
    def get_summary(self):

        active = self.current_active

        if not active:
            return {
                "tracked_objects": 0,
                "average_path_length": 0,
                "average_distance": 0,
                "total_distance": 0
            }

        path_lengths = [
            len(self.paths[track_id])
            for track_id in active
            if track_id in self.paths
        ]

        distances = [
            self.total_distance.get(track_id, 0.0)
            for track_id in active
        ]

        total_distance = sum(distances)

        return {

            "tracked_objects": len(active),

            "average_path_length": round(
                sum(path_lengths) / len(path_lengths),
                2
            ) if path_lengths else 0,

            "average_distance": round(
                total_distance / len(distances),
                2
            ) if distances else 0,

            "total_distance": round(
                total_distance,
                2
            )
        }

    # =====================================================
    # GLOBAL DIRECTION ANALYTICS
    # =====================================================
    def get_direction_summary(self):

        counts = {}

        for track_id in self.current_active:

            direction = self.get_track_direction(track_id)

            counts[direction] = (
                counts.get(direction, 0) + 1
            )

        return {

            "tracked_objects": len(
                self.current_active
            ),

            "directions": counts
        }


trajectory = TrajectoryAnalytics()