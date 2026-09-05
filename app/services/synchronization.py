# app/services/synchronization.py

import time


class CameraSynchronization:
    """
    Multi-camera synchronization service.

    Responsibilities
    ----------------
    • Camera timestamps
    • Frame timestamps
    • Camera heartbeat
    • Synchronization monitoring

    Future:
    • Cross-camera alignment
    • Clock drift detection
    """

    def __init__(self):

        self.camera_frames = {}

    # =====================================
    # UPDATE CAMERA FRAME
    # =====================================
    def update(
        self,
        camera_id,
        frame_number
    ):

        self.camera_frames[camera_id] = {

            "frame_number": frame_number,

            "timestamp": time.time()
        }

    # =====================================
    # CAMERA STATE
    # =====================================
    def get_camera_state(
        self,
        camera_id
    ):

        return self.camera_frames.get(
            camera_id,
            {}
        )

    # =====================================
    # SUMMARY
    # =====================================
    def get_summary(self):

        return {

            "active_cameras": len(
                self.camera_frames
            ),

            "cameras": self.camera_frames
        }


synchronization = CameraSynchronization()