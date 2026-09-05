# app/services/heatmap.py

import numpy as np
import cv2


class HeatmapManager:
    """
    Crowd heatmap analytics.

    Records where people have been observed over time.
    """

    def __init__(self):

        # Historical (never decays)
        self.historical_heatmap = None

        # Live (decays continuously)
        self.live_heatmap = None

        self.total_points = 0

        self.decay = 0.995

    # =====================================
    # INITIALIZE
    # =====================================
    def initialize(self, frame_shape):

        height, width = frame_shape[:2]

        if (
            self.live_heatmap is None or
            self.live_heatmap.shape != (height, width)
        ):
            self.historical_heatmap = np.zeros(
                (height, width),
                dtype=np.float32
            )

            self.live_heatmap = np.zeros(
                (height, width),
                dtype=np.float32
            )

    # =====================================
    # DECAY
    # =====================================
    def decay_heat(self):

        if self.live_heatmap is None:
            return

        self.live_heatmap *= self.decay

    # =====================================
    # UPDATE
    # =====================================
    # =====================================
    # UPDATE
    # =====================================
    def update(self, cx, cy, radius=20, intensity=1.0):

        if self.live_heatmap is None:
            return

        # Create a temporary mask
        mask = np.zeros_like(
            self.live_heatmap,
            dtype=np.float32
        )

        cv2.circle(
            mask,
            (cx, cy),
            radius,
            intensity,
            -1
        )

        # Historical accumulates forever
        self.historical_heatmap += mask

        # Live continuously decays + accumulates
        self.live_heatmap += mask

        self.total_points += 1

    # =====================================
    # RESET
    # =====================================
    def reset(self):

        if self.live_heatmap is not None:
            self.live_heatmap.fill(0)

        if self.historical_heatmap is not None:
            self.historical_heatmap.fill(0)

        self.total_points = 0

    # =====================================
    # OVERLAY
    # =====================================
    def get_overlay(self, mode="live"):

        heatmap = (
            self.live_heatmap
            if mode == "live"
            else self.historical_heatmap
        )

        if heatmap is None:
            return None

        max_heat = np.max(heatmap)

        if max_heat == 0:
            normalized = np.zeros_like(
                heatmap,
                dtype=np.uint8
            )
        else:
            normalized = (
                    heatmap / max_heat * 255
            ).astype(np.uint8)

        return cv2.applyColorMap(
            normalized,
            cv2.COLORMAP_JET
        )

    # =====================================
    # STATISTICS
    # =====================================
    def get_statistics(self, mode="live"):

        heatmap = (
            self.live_heatmap
            if mode == "live"
            else self.historical_heatmap
        )

        if heatmap is None:
            return {
                "mode": mode,
                "total_points": 0,
                "hottest_pixel": 0,
                "coverage": 0.0
            }

        hottest = float(np.max(heatmap))

        coverage = (
                np.count_nonzero(heatmap)
                / heatmap.size
                * 100
        )

        return {

            "mode": mode,

            "total_points": self.total_points,

            "hottest_pixel": round(hottest, 2),

            "coverage": round(float(coverage), 2)
        }

    def get_heatmap(self, mode="live"):

        return (
            self.live_heatmap
            if mode == "live"
            else self.historical_heatmap
        )

heatmap = HeatmapManager()

