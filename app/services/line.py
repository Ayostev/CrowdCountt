# app/services/line.py

import cv2
import time

class LineManager:
    """
    Production-grade multi-line event engine
    """

    def __init__(self, config_lines):

        self.lines = {}
        self.history = {}
        self.counts = {}
        self.crossed = {}

        # optional event buffer (IMPORTANT FOR DASHBOARD)
        self.events = []
        # Flow analytics
        self.start_time = time.time()
        self.flow_window = 60  # seconds

        for line in config_lines:

            name = line["name"]

            self.lines[name] = {
                "start": tuple(line["start"]),
                "end": tuple(line["end"])
            }

            self.counts[name] = 0
            self.crossed[name] = set()

        self.active_ids = set()

    # ==============================
    # FRAME RESET
    # ==============================
    def reset_frame(self):
        self.active_ids.clear()

    # ==============================
    # UPDATE
    # ==============================
    def update(self, track_id, cx, cy):

        self.active_ids.add(track_id)

        if track_id not in self.history:
            self.history[track_id] = []

        self.history[track_id].append((cx, cy))

        if len(self.history[track_id]) > 20:
            self.history[track_id].pop(0)

        self._check_crossing(track_id)

    # ==============================
    # CROSS DETECTION
    # ==============================
    def _check_crossing(self, track_id):

        history = self.history.get(track_id, [])
        if len(history) < 2:
            return

        p1, p2 = history[-2], history[-1]

        for name, line in self.lines.items():

            if track_id in self.crossed[name]:
                continue

            if self._intersect(p1, p2, line["start"], line["end"]):

                self.counts[name] += 1
                self.crossed[name].add(track_id)

                # =========================
                # EVENT LOG (FOR FUSION)
                # =========================
                self.events.append({
                    "track_id": track_id,
                    "type": "cross",
                    "line": name,
                    "time": time.time()
                })

    # ==============================
    # GEOMETRY
    # ==============================
    def _intersect(self, p1, p2, q1, q2):

        def ccw(a, b, c):
            return (c[1]-a[1]) * (b[0]-a[0]) > (b[1]-a[1]) * (c[0]-a[0])

        return (ccw(p1, q1, q2) != ccw(p2, q1, q2)) and \
               (ccw(p1, p2, q1) != ccw(p1, p2, q2))

    # ==============================
    # GETTERS
    # ==============================
    def get_counts(self):
        return {
            "entry": self.counts.get("entry", 0),
            "exit": self.counts.get("exit", 0)
        }

    def get_active_ids(self):
        return list(self.active_ids)

    def get_events(self):
        return self.events

    def get_recent_events(self, seconds=60):

        now = time.time()

        return [
            event
            for event in self.events
            if now - event["time"] <= seconds
        ]

    def get_flow_metrics(self):

        recent = self.get_recent_events(self.flow_window)

        entry = sum(
            1 for e in recent
            if e["line"] == "entry"
        )

        exit = sum(
            1 for e in recent
            if e["line"] == "exit"
        )

        uptime = max(
            time.time() - self.start_time,
            1
        )

        return {

            "entry_total": self.counts.get("entry", 0),

            "exit_total": self.counts.get("exit", 0),

            "entry_last_minute": entry,

            "exit_last_minute": exit,

            "entry_rate_per_min": round(entry, 2),

            "exit_rate_per_min": round(exit, 2),

            "net_flow": entry - exit,

            "uptime": round(uptime, 1)
        }

    # ==============================
    # DRAW
    # ==============================
    def draw(self, frame):

        for name, line in self.lines.items():

            cv2.line(frame, line["start"], line["end"], (0, 0, 255), 2)

            cv2.putText(
                frame,
                name,
                line["start"],
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2
            )


# GLOBAL INSTANCE (CRITICAL FIX)
line_manager = LineManager([
    {"name": "entry", "start": [0, 450], "end": [1280, 450]},
    {"name": "exit", "start": [0, 600], "end": [1280, 600]}
])