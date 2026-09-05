# app/services/crowd_metrics.py

import time
from collections import deque


class CrowdMetrics:
    """
    Crowd-level analytics engine.

    Computes global statistics only.
    Does NOT store per-track analytics.
    """

    def __init__(self):

        # ==========================
        # Runtime
        # ==========================
        self.start_time = time.time()

        # ==========================
        # Occupancy
        # ==========================
        self.current_occupancy = 0
        self.peak_occupancy = 0

        self.total_samples = 0
        self.occupancy_sum = 0

        # occupancy history
        self.history = deque(maxlen=300)

        # ==========================
        # Flow
        # ==========================
        self.total_entries = 0
        self.total_exits = 0

        self.last_entries = 0
        self.last_exits = 0

        self.entry_rate = 0.0
        self.exit_rate = 0.0

        self.last_update = time.time()

        # ==========================
        # Zones
        # ==========================
        self.zone_counts = {}

    # =====================================================
    # UPDATE (Called once per frame)
    # =====================================================
    def update(self,
               active_tracks,
               entries,
               exits,
               zones):

        now = time.time()

        # --------------------------------
        # Occupancy
        # --------------------------------
        self.current_occupancy = len(active_tracks)

        if self.current_occupancy > self.peak_occupancy:
            self.peak_occupancy = self.current_occupancy

        self.total_samples += 1
        self.occupancy_sum += self.current_occupancy

        self.history.append({
            "time": now,
            "occupancy": self.current_occupancy
        })

        # --------------------------------
        # Flow
        # --------------------------------
        elapsed = max(now - self.last_update, 1e-6)

        new_entries = entries - self.last_entries
        new_exits = exits - self.last_exits

        self.entry_rate = (new_entries / elapsed) * 60.0
        self.exit_rate = (new_exits / elapsed) * 60.0

        self.total_entries = entries
        self.total_exits = exits

        self.last_entries = entries
        self.last_exits = exits
        self.last_update = now

        # --------------------------------
        # Zones
        # --------------------------------
        self.zone_counts = dict(zones)

    # =====================================================
    # GETTERS
    # =====================================================
    def get_metrics(self):

        avg_occ = 0

        if self.total_samples > 0:
            avg_occ = (
                self.occupancy_sum /
                self.total_samples
            )

        return {

            "current_occupancy": self.current_occupancy,

            "average_occupancy": round(avg_occ, 2),

            "peak_occupancy": self.peak_occupancy,

            "entry_rate": round(self.entry_rate, 2),

            "exit_rate": round(self.exit_rate, 2),

            "uptime_seconds": round(
                time.time() - self.start_time,
                1
            ),

            "zones": dict(self.zone_counts)
        }

    # =====================================================
    # HISTORY
    # =====================================================
    def get_history(self):

        return list(self.history)


crowd_metrics = CrowdMetrics()