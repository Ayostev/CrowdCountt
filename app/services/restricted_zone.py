# app/services/restricted_zone.py

import time
from collections import defaultdict

class RestrictedZoneAnalytics:
    """
    Restricted Zone Violations

    Detect:
    - entry into restricted zones
    - prolonged stay
    - repeated violations
    """

    VIOLATION_DURATION = 10

    def __init__(self):
        self.active_violations = set()
        self.entry_time = {}
        self.violation_counts = defaultdict(int)
        self.violation_history = []

    # =====================================
    # UPDATE
    # =====================================
    def update(self, global_id, camera_id, zone_name, restricted_zones):
        now = time.time()

        print(
            "[RESTRICTED UPDATE]",
            global_id,
            camera_id,
            zone_name
        )

        print(
            "[RESTRICTED CHECK]",
            zone_name,
            restricted_zones
        )
        if zone_name not in restricted_zones:
            self.entry_time.pop(global_id, None)
            self.active_violations.discard(global_id)
            return

        if global_id not in self.entry_time:
            self.entry_time[global_id] = now
            self.violation_counts[global_id] += 1
            self.violation_history.append({
                "global_id": global_id,
                "camera_id": camera_id,
                "zone": zone_name,
                "time": now,
                "type": "restricted_entry"
            })

        duration = now - self.entry_time[global_id]
        if duration >= self.VIOLATION_DURATION:
            self.active_violations.add(global_id)

    # =====================================
    # VIOLATION STATUS
    # =====================================
    def is_violating(self, global_id):
        return global_id in self.active_violations

    # =====================================
    # SUMMARY
    # =====================================
    def get_summary(self):
        return {
            "active_violations": len(self.active_violations),
            "global_ids": sorted(self.active_violations),
            "recent_events": self.violation_history[-20:]
        }


restricted_zone = RestrictedZoneAnalytics()
