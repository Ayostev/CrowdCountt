from ultralytics import YOLO
import cv2
import json

from app.services.fusion import fusion
from app.services.zones import zones
from app.services.line import line_manager
from app.services.reid import reid
from app.services.reid_matcher import reid_matcher




class PersonDetector:

    def __init__(self):

        print("[Detector] Loading YOLOv8 model...")
        self.model = YOLO("yolov8n.pt")
        print("[Detector] ✅ YOLO loaded")

        # =========================
        # LOAD CONFIG (ONLY FOR DRAWING)
        # =========================
        with open("config/zones.json", "r") as f:
            self.config = json.load(f)

    # ======================================================
    # MAIN PIPELINE
    # ======================================================
    def detect(self, frame, camera_id="cam_1"):
        fusion.initialize_frame(frame)

        # ==================================================
        # RUN YOLO + BYTE TRACK
        # ==================================================
        results = self.model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            classes=[0]
        )

        person_count = 0

        # ==================================================
        # DRAW (VISUAL ONLY - NO LOGIC)
        # ==================================================
        zones.draw(frame)
        line_manager.draw(frame)

        # ==================================================
        # PROCESS DETECTIONS
        # ==================================================
        if results[0].boxes.id is not None:

            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.cpu().numpy()
            confs = results[0].boxes.conf.cpu().numpy()

            for box, track_id, conf in zip(boxes, ids, confs):
                track_id = int(track_id)

                x1, y1, x2, y2 = map(int, box)
                person_count += 1

                # =========================
                # CENTER POINT
                # =========================
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)

                # =========================
                # BUILD APPEARANCE SIGNATURE
                # =========================
                signature = reid_matcher.build_detection_signature(
                    camera_id=camera_id,
                    frame=frame,
                    bbox=(x1, y1, x2, y2)
                )

                # =========================
                # CHECK FOR REID REACTIVATION
                # =========================
                reactivation = None

                if signature is not None:
                    reactivation = (
                        reid_matcher.find_reactivation_candidate(
                            camera_id=camera_id,
                            signature=signature
                        )
                    )

                # =========================
                # GLOBAL ID DECISION
                # =========================

                if reactivation is not None:

                    # ---------------------------------
                    # Existing LOST identity found
                    # ---------------------------------

                    global_id = reactivation["global_id"]

                    print(
                        "[REID REACTIVATION]",
                        f"global_id={global_id}",
                        f"camera={camera_id}",
                        f"local_track_id={track_id}",
                        f"confidence={reactivation['confidence']}"
                    )

                    # Reactivate existing global identity
                    fusion.update(
                        track_id,
                        cx,
                        cy,
                        global_id=global_id,
                        camera_id=camera_id
                    )

                else:

                    # ---------------------------------
                    # Normal new-track registration
                    # ---------------------------------

                    fusion.update(
                        track_id,
                        cx,
                        cy,
                        camera_id=camera_id
                    )

                    global_id = fusion.get_global_id(
                        camera_id,
                        track_id
                    )
                reid.update_signature(
                    global_id=global_id,
                    camera_id=camera_id,
                    frame=frame,
                    bbox=(x1, y1, x2, y2)
                )

                

                # =========================
                # DRAW CENTER POINT
                # =========================
                cv2.circle(frame, (cx, cy), 5, (255, 0, 0), -1)

                # =========================
                # DRAW BOX
                # =========================
                label = f"ID {track_id} | {conf:.2f}"

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    frame,
                    label,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )

        # ==================================================
        # FINALIZE FRAME ANALYTICS
        # ==================================================
        fusion.finalize_frame()


        # ==================================================
        # GET GLOBAL STATE FROM FUSION (ONLY SOURCE)
        # ==================================================
        stats = fusion.get_global_stats()

        # -------- TEMP DEBUG --------
        print(stats["trajectory"])
        # ----------------------------
        dwell = fusion.get_dwell_summary()

        avg_dwell = dwell["average_dwell"]
        max_dwell = dwell["maximum_dwell"]

        speed = fusion.get_speed_summary()

        avg_speed = speed["average_speed"]
        max_speed = speed["maximum_speed"]
        fast_movers = speed["fast_movers"]

        # ==================================================
        # OVERLAY STATS
        # ==================================================
        cv2.putText(frame, f"People Count: {person_count}",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (0, 255, 255), 3)

        cv2.putText(
            frame,
            f"IN: {stats.get('entries', 0)}",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            3
        )

        cv2.putText(
            frame,
            f"OUT: {stats.get('exits', 0)}",
            (20, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            3
        )

        cv2.putText(frame, f"AVG STAY: {avg_dwell:.1f}s",
                    (20, 200),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (255, 255, 255), 2)

        cv2.putText(frame, f"MAX STAY: {max_dwell:.1f}s",
                    (20, 235),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (255, 255, 255), 2)
        cv2.putText(
            frame,
            f"AVG SPEED: {avg_speed:.1f}px/s",
            (20, 270),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 0),
            2
        )

        cv2.putText(
            frame,
            f"MAX SPEED: {max_speed:.1f}px/s",
            (20, 305),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 0),
            2
        )

        cv2.putText(
            frame,
            f"FAST MOVERS: {fast_movers}",
            (20, 340),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2
        )

        # ==================================================
        # ZONE DISPLAY (FROM FUSION ONLY)
        # ==================================================
        zone_counts = stats["zones"]

        y_pos = 385

        for zone_name, count in zone_counts.items():

            cv2.putText(
                frame,
                f"{zone_name}: {count}",
                (20, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 0, 255),
                2
            )

            y_pos += 30

        return frame


# Global singleton
detector = PersonDetector()