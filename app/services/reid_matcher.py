# app/services/reid_matcher.py

import math
import cv2

from app.services.reid import reid
from app.services.merge_engine import merge_engine
from app.services.global_registry import global_registry

class ReIDMatcher:
    """
    Cross-Camera Candidate Matching

    Phase 1:
    Lightweight appearance matching.

    Future:
    Deep ReID embeddings.
    """

    ALLOW_SAME_CAMERA_MATCHES = False

    COLOR_THRESHOLD = 50
    HEIGHT_THRESHOLD = 150
    ASPECT_THRESHOLD = 0.15

    REACTIVATION_THRESHOLD = 0.90

    def __init__(self):

        self.matches = []

    # =====================================
    # COLOR DISTANCE
    # =====================================
    def color_distance(
        self,
        color1,
        color2
    ):

        return math.sqrt(

            (color1[0] - color2[0]) ** 2 +

            (color1[1] - color2[1]) ** 2 +

            (color1[2] - color2[2]) ** 2
        )

    # =====================================
    # FIND MATCHES
    # =====================================
    def find_candidates(self):

        print("FIND_CANDIDATES CALLED")

        self.matches.clear()

        signatures = list(
            reid.signatures.values()
        )

        print(
            "SIGNATURE COUNT =",
            len(signatures)
        )

        print(
            "ALLOW_SAME_CAMERA_MATCHES =",
            self.ALLOW_SAME_CAMERA_MATCHES
        )

        self.matches.clear()

        signatures = list(
            reid.signatures.values()
        )

        print(
            "SIGNATURE COUNT =",
            len(signatures)
        )

        for i in range(len(signatures)):

            sig1 = signatures[i]

            for j in range(i + 1, len(signatures)):

                sig2 = signatures[j]

                print(
                    "COMPARING",
                    sig1["global_id"],
                    sig2["global_id"]
                )

                try:

                    camera_count = len(
                        set(
                            s["camera_id"]
                            for s in signatures
                        )
                    )

                    if (
                            camera_count > 1
                            and
                            not self.ALLOW_SAME_CAMERA_MATCHES
                            and
                            sig1["camera_id"] == sig2["camera_id"]
                    ):
                        continue

                    if (
                            not self.ALLOW_SAME_CAMERA_MATCHES
                            and
                            sig1["camera_id"]
                            ==
                            sig2["camera_id"]
                    ):
                        continue

                    confidence = self.compute_confidence(
                        sig1,
                        sig2
                    )

                    if confidence >= 0.90:
                        merge_engine.merge(

                            sig1["global_id"],

                            sig2["global_id"],

                            confidence
                        )

                    print(
                        sig1["global_id"],
                        sig2["global_id"],
                        confidence
                    )

                    if confidence >= 0.70:
                        self.matches.append({

                            "source_global_id":
                                sig1["global_id"],

                            "target_global_id":
                                sig2["global_id"],

                            "source_camera":
                                sig1["camera_id"],

                            "target_camera":
                                sig2["camera_id"],

                            "confidence":
                                round(confidence, 2)
                        })

                except Exception as e:

                    print(
                        "[REID MATCH ERROR]",
                        e,
                        sig1,
                        sig2
                    )

        return self.matches
    # =====================================
    # CONFIDENCE SCORE
    # =====================================
    def compute_confidence(
        self,
        sig1,
        sig2
    ):

        score = 0.0

        # --------------------------------
        # Color similarity
        # --------------------------------
        color_dist = self.color_distance(
            sig1["color"],
            sig2["color"]
        )

        if color_dist <= self.COLOR_THRESHOLD:
            score += 0.4

        # --------------------------------
        # Height similarity
        # --------------------------------
        if abs(
            sig1["height"]
            -
            sig2["height"]
        ) <= self.HEIGHT_THRESHOLD:

            score += 0.3

        # --------------------------------
        # Aspect similarity
        # --------------------------------
        if abs(
            sig1["aspect_ratio"]
            -
            sig2["aspect_ratio"]
        ) <= self.ASPECT_THRESHOLD:

            score += 0.3

        return score

    # =====================================
    # BUILD DETECTION SIGNATURE
    # =====================================
    def build_detection_signature(
            self,
            camera_id,
            frame,
            bbox
    ):

        x1, y1, x2, y2 = bbox

        h, w = frame.shape[:2]

        x1 = max(0, x1)
        y1 = max(0, y1)

        x2 = min(w, x2)
        y2 = min(h, y2)

        crop = frame[y1:y2, x1:x2]

        if crop.size == 0:
            return None

        mean_color = cv2.mean(crop)[:3]

        width = x2 - x1
        height = y2 - y1

        aspect_ratio = 0

        if height > 0:
            aspect_ratio = width / height

        return {
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
            )
        }

    # =====================================
    # FIND LOST GLOBAL ID CANDIDATE
    # =====================================
    def find_reactivation_candidate(
            self,
            camera_id,
            signature
    ):

        best_match = None
        best_confidence = 0.0

        # ---------------------------------
        # Get LOST global identities
        # ---------------------------------

        lost_tracks = (
            global_registry.get_lost_tracks()
        )

        # ---------------------------------
        # Search their ReID signatures
        # ---------------------------------

        for track in lost_tracks:

            candidate_global_id = (
                track["global_id"]
            )

            # ---------------------------------
            # SAFETY: ONLY LOST IDENTITIES
            # ---------------------------------

            if track.get("status") != "lost":
                continue

            # ---------------------------------
            # SAFETY: IDENTITY MUST STILL EXIST
            # ---------------------------------

            current_track = global_registry.get_track(
                candidate_global_id
            )

            if current_track is None:
                continue

            # ---------------------------------
            # SAFETY: NEVER REACTIVATE ACTIVE ID
            # ---------------------------------

            if current_track.get("status") == "active":
                continue

            # ---------------------------------
            # SAFETY: EXPIRED IDs are invalid
            # ---------------------------------

            if current_track.get("status") == "expired":
                continue

            candidate = reid.get_signature(
                candidate_global_id
            )

            if candidate is None:
                continue

            # ---------------------------------
            # Same camera protection
            # ---------------------------------

            if (
                    not self.ALLOW_SAME_CAMERA_MATCHES
                    and
                    candidate["camera_id"] == camera_id
            ):
                continue

            # ---------------------------------
            # Calculate appearance similarity
            # ---------------------------------

            confidence = self.compute_confidence(
                signature,
                candidate
            )

            # ---------------------------------
            # Keep strongest candidate
            # ---------------------------------

            if confidence > best_confidence:
                best_confidence = confidence

                best_match = {
                    "global_id":
                        candidate_global_id,

                    "camera_id":
                        candidate["camera_id"],

                    "confidence":
                        round(confidence, 2)
                }

        # ---------------------------------
        # No candidate
        # ---------------------------------

        # ---------------------------------
        # No candidate
        # ---------------------------------

        if best_match is None:
            return None

        # ---------------------------------
        # Verify candidate still exists
        # ---------------------------------

        candidate_track = global_registry.get_track(
            best_match["global_id"]
        )

        if candidate_track is None:
            return None

        # ---------------------------------
        # Candidate MUST still be LOST
        # ---------------------------------

        if candidate_track.get("status") != "lost":
            return None

        # ---------------------------------
        # Strong match required
        # ---------------------------------

        if best_confidence < self.REACTIVATION_THRESHOLD:
            return None

        return best_match

    # =====================================
    # SUMMARY
    # =====================================
    def get_summary(self):

        try:

            self.find_candidates()

            return {

            "candidate_matches": len(
                self.matches
            ),

            "matches": self.matches
            }
        except Exception as e:
            return {
                "error": str(e),
                "candidate_matches": 0,
                "matches": []
            }




reid_matcher = ReIDMatcher()