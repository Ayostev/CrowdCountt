# app/services/reid.py

import time
import cv2


class ReIDEngine:
    """
    Cross-Camera Re-Identification

    Phase 1:
    Lightweight appearance signatures.

    Future:
    Deep embeddings.
    """
    SIGNATURE_TIMEOUT = 30
    MAX_SIGNATURES = 1000

    def __init__(self):

        # global_id -> signature
        self.signatures = {}
        self.last_cleanup = 0

    # =====================================
    # APPEARANCE SIGNATURE
    # =====================================
    def update_signature(
        self,
        global_id,
        camera_id,
        frame,
        bbox
    ):
        now = time.time()

        if now - self.last_cleanup > 5:
            self.cleanup()

            self.last_cleanup = now

        x1, y1, x2, y2 = bbox

        h, w = frame.shape[:2]

        x1 = max(0, x1)
        y1 = max(0, y1)

        x2 = min(w, x2)
        y2 = min(h, y2)

        crop = frame[y1:y2, x1:x2]

        if crop.size == 0:
            return

        mean_color = cv2.mean(crop)[:3]

        width = x2 - x1
        height = y2 - y1

        aspect_ratio = 0

        if height > 0:
            aspect_ratio = width / height

        self.signatures[global_id] = {

            "global_id": global_id,

            "camera_id": camera_id,

            "color": [
                round(mean_color[0], 2),
                round(mean_color[1], 2),
                round(mean_color[2], 2)
            ],

            "width": width,

            "height": height,

            "aspect_ratio": round(
                aspect_ratio,
                3
            ),

            "updated_at": time.time()
        }

    # =====================================
    # CLEANUP OLD SIGNATURES
    # =====================================
    def cleanup(self):

        before_count = len(
            self.signatures
        )

        now = time.time()

        expired = []

        for global_id, sig in list(
                self.signatures.items()
        ):

            age = now - sig["updated_at"]

            if age > self.SIGNATURE_TIMEOUT:
                expired.append(global_id)

        for global_id in expired:
            del self.signatures[global_id]

        # Emergency protection
        if len(self.signatures) > self.MAX_SIGNATURES:

            sorted_items = sorted(

                self.signatures.items(),

                key=lambda x:
                x[1]["updated_at"]
            )

            excess = (
                    len(self.signatures)
                    -
                    self.MAX_SIGNATURES
            )

            for global_id, _ in sorted_items[:excess]:
                del self.signatures[global_id]

        after_count = len(
            self.signatures
        )

        if before_count != after_count:
            print(

                f"[REID CLEANUP] "
                f"before={before_count} "
                f"removed={before_count - after_count} "
                f"after={after_count}"

            )
    # =====================================
    # LOOKUP
    # =====================================
    def get_signature(self, global_id):

        return self.signatures.get(global_id)

    # =====================================
    # SUMMARY
    # =====================================
    def get_summary(self):

        self.cleanup()

        return {

            "tracked_signatures": len(
                self.signatures
            ),

            "signatures": list(
                self.signatures.values()
            )
        }


reid = ReIDEngine()