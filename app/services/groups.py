# app/services/groups.py

import math


class GroupAnalytics:

    GROUP_DISTANCE = 100
    MIN_GROUP_SIZE = 2

    def __init__(self):

        self.positions = {}

        self.groups = []

        self.previous_groups = []

        self.merge_events = []

        self.split_events = []

    # =====================================
    # UPDATE POSITION
    # =====================================
    def update(self, track_id, cx, cy):

        self.positions[track_id] = (cx, cy)

    # =====================================
    # FRAME FINALIZATION
    # =====================================
    def finalize_frame(self, active_tracks):

        active_tracks = list(active_tracks)

        self.previous_groups = [
            set(g)
            for g in self.groups
        ]

        self.groups = []

        visited = set()

        for track_id in active_tracks:

            if track_id in visited:
                continue

            group = {track_id}

            x1, y1 = self.positions.get(
                track_id,
                (None, None)
            )

            if x1 is None:
                continue

            for other_id in active_tracks:

                if other_id == track_id:
                    continue

                x2, y2 = self.positions.get(
                    other_id,
                    (None, None)
                )

                if x2 is None:
                    continue

                distance = math.hypot(
                    x2 - x1,
                    y2 - y1
                )

                if distance <= self.GROUP_DISTANCE:

                    group.add(other_id)

            visited.update(group)

            if len(group) >= self.MIN_GROUP_SIZE:

                self.groups.append(group)

        self._detect_merges()
        self._detect_splits()

    # =====================================
    # MERGES
    # =====================================
    def _detect_merges(self):

        if len(self.previous_groups) < 2:
            return

        for group in self.groups:

            overlaps = 0

            for previous in self.previous_groups:

                if group & previous:
                    overlaps += 1

            if overlaps >= 2:

                self.merge_events.append({

                    "type": "merge",

                    "group_size": len(group)
                })

    # =====================================
    # SPLITS
    # =====================================
    def _detect_splits(self):

        if len(self.groups) < 2:
            return

        for previous in self.previous_groups:

            overlaps = 0

            for group in self.groups:

                if previous & group:
                    overlaps += 1

            if overlaps >= 2:

                self.split_events.append({

                    "type": "split",

                    "original_size": len(previous)
                })

    # =====================================
    # TRACK GROUP
    # =====================================
    def get_track_group(self, track_id):

        for group in self.groups:

            if track_id in group:

                return {

                    "in_group": True,

                    "group_size": len(group),

                    "members": sorted(group)
                }

        return {

            "in_group": False,

            "group_size": 0,

            "members": []
        }

    # =====================================
    # SUMMARY
    # =====================================
    def get_summary(self):

        return {

            "active_groups": len(
                self.groups
            ),

            "largest_group": max(
                [len(g) for g in self.groups],
                default=0
            ),

            "merge_events": self.merge_events[-20:],

            "split_events": self.split_events[-20:]
        }


groups = GroupAnalytics()