# app/services/global_registry.py

import time


class GlobalTrackRegistry:
    """
    Multi-Camera Global Identity Registry

    Responsibilities
    ----------------
    • Assign global IDs
    • Prevent ID collisions across cameras
    • Maintain camera/local-track -> global-track mappings
    • Track current camera ownership
    • Track camera history
    • Support cross-camera identity persistence
    • Safely remove expired registry entries

    Architecture
    ------------
    (camera_id, local_track_id) -> global_id

    global_id -> global identity metadata

    A single global identity may therefore have
    different local track IDs on different cameras.
    """

    REGISTRY_TIMEOUT = 30
    CLEANUP_INTERVAL = 5

    def __init__(self):

        # ---------------------------------
        # GLOBAL ID GENERATOR
        # ---------------------------------

        self.next_global_id = 1000

        # ---------------------------------
        # LOCAL -> GLOBAL MAPPING
        #
        # (camera_id, local_track_id)
        # -> global_id
        # ---------------------------------

        self.track_map = {}

        # ---------------------------------
        # GLOBAL -> IDENTITY METADATA
        #
        # global_id -> metadata
        # ---------------------------------

        self.global_tracks = {}

        # ---------------------------------
        # LAST CLEANUP
        # ---------------------------------

        self.last_cleanup = time.time()

    # =====================================
    # REGISTER TRACK
    # =====================================

    # =====================================
    # REGISTER TRACK
    # =====================================
    def register_track(
            self,
            camera_id,
            local_track_id
    ):

        now = time.time()

        key = (
            camera_id,
            local_track_id
        )

        # =====================================
        # EXISTING LOCAL TRACK
        # =====================================

        if key in self.track_map:

            global_id = self.track_map[key]

            track = self.global_tracks.get(
                global_id
            )

            if track:

                track["last_seen"] = now

                track["current_camera"] = camera_id

                track["last_camera"] = camera_id

                track["local_track_id"] = local_track_id

                track["last_local_track_id"] = local_track_id

                track["status"] = "active"

                track["lost_at"] = None

                track["expired_at"] = None

                track["local_tracks"][
                    camera_id
                ] = local_track_id

                if camera_id not in track[
                    "camera_history"
                ]:
                    track[
                        "camera_history"
                    ].append(camera_id)

            self._run_cleanup(now)

            return global_id

        # =====================================
        # NEW GLOBAL ID
        # =====================================

        self.next_global_id += 1

        global_id = self.next_global_id

        self.track_map[key] = global_id

        self.global_tracks[global_id] = {

            "global_id": global_id,

            # Camera state
            "current_camera": camera_id,

            "first_camera": camera_id,

            "last_camera": camera_id,

            "camera_history": [
                camera_id
            ],

            # Local tracking
            "local_track_id": local_track_id,

            "last_local_track_id": local_track_id,

            "local_tracks": {
                camera_id: local_track_id
            },

            # Lifecycle
            "status": "active",

            "lost_at": None,

            "expired_at": None,

            # Timing
            "first_seen": now,

            "last_seen": now
        }

        self._run_cleanup(now)

        return global_id
    # =====================================
    # UPDATE CAMERA
    # =====================================

    # =====================================
    # CAMERA TRANSITION
    # =====================================
    def update_camera(
            self,
            global_id,
            camera_id,
            local_track_id=None
    ):

        track = self.global_tracks.get(
            global_id
        )

        if track is None:
            return False

        now = time.time()

        previous_camera = track[
            "current_camera"
        ]

        # =====================================
        # CAMERA CHANGE
        # =====================================

        if previous_camera != camera_id:

            track[
                "current_camera"
            ] = camera_id

            track[
                "last_camera"
            ] = camera_id

            if camera_id not in track[
                "camera_history"
            ]:
                track[
                    "camera_history"
                ].append(camera_id)

        # =====================================
        # LOCAL TRACK UPDATE
        # =====================================

        if local_track_id is not None:
            track[
                "local_track_id"
            ] = local_track_id

            track[
                "last_local_track_id"
            ] = local_track_id

            track[
                "local_tracks"
            ][camera_id] = local_track_id

            self.track_map[
                (camera_id, local_track_id)
            ] = global_id

        # =====================================
        # REACTIVATE IDENTITY
        # =====================================

        track["status"] = "active"

        track["lost_at"] = None

        track["expired_at"] = None

        track["last_seen"] = now

        return True

    # =====================================
    # GLOBAL ID REACTIVATION
    # =====================================
    def reactivate_track(
            self,
            global_id,
            camera_id,
            local_track_id
    ):

        track = self.global_tracks.get(
            global_id
        )

        if track is None:
            return False

        now = time.time()

        # =====================================
        # EXPIRED IDs CANNOT BE REACTIVATED
        # =====================================

        if track.get("status") == "expired":
            return False

        previous_camera = track.get(
            "current_camera"
        )

        # =====================================
        # CAMERA TRANSITION
        # =====================================

        if previous_camera != camera_id:

            track["current_camera"] = camera_id

            track["last_camera"] = camera_id

            if camera_id not in track[
                "camera_history"
            ]:
                track[
                    "camera_history"
                ].append(camera_id)

        # =====================================
        # LOCAL TRACK MAPPING
        # =====================================

        track["local_track_id"] = local_track_id

        track[
            "last_local_track_id"
        ] = local_track_id

        track[
            "local_tracks"
        ][camera_id] = local_track_id

        self.track_map[
            (camera_id, local_track_id)
        ] = global_id

        # =====================================
        # REACTIVATE
        # =====================================

        track["status"] = "active"

        track["lost_at"] = None

        track["expired_at"] = None

        track["last_seen"] = now

        return True

    # =====================================
    # LOST GLOBAL TRACKS
    # =====================================
    def get_lost_tracks(self):

        return [
            track
            for track in self.global_tracks.values()
            if track.get("status") == "lost"
        ]

    # =====================================
    # GLOBAL OCCUPANCY
    # =====================================
    def get_global_occupancy(self):

        return sum(
            1
            for track in self.global_tracks.values()
            if track.get("status") == "active"
        )

    # =====================================
    # GLOBAL OCCUPANCY BY CAMERA
    # =====================================
    def get_global_occupancy_by_camera(self):

        occupancy = {}

        for track in self.global_tracks.values():

            # Only active global identities count
            if track.get("status") != "active":
                continue

            camera_id = track.get(
                "current_camera"
            )

            if camera_id is None:
                continue

            occupancy[camera_id] = (
                occupancy.get(camera_id, 0) + 1
            )

        return occupancy
    # =====================================
    # REACTIVATION CANDIDATE
    # =====================================
    def get_reactivation_candidate(
            self,
            global_id
    ):

        track = self.global_tracks.get(
            global_id
        )

        if not track:
            return None

        if track.get("status") != "lost":
            return None

        return track

    # =====================================
    # GLOBAL ID LOOKUP
    # =====================================

    def get_global_id(
        self,
        camera_id,
        local_track_id
    ):

        return self.track_map.get(
            (
                camera_id,
                local_track_id
            )
        )

    # =====================================
    # GLOBAL TRACK LOOKUP
    # =====================================

    def get_track(
        self,
        global_id
    ):

        return self.global_tracks.get(
            global_id
        )

    # =====================================
    # GLOBAL TRACK EXISTS
    # =====================================

    def exists(
        self,
        global_id
    ):

        return global_id in self.global_tracks

    # =====================================
    # PERIODIC CLEANUP
    # =====================================

    def _run_cleanup(self, now=None):

        if now is None:
            now = time.time()

        if (
                now - self.last_cleanup
                >
                self.CLEANUP_INTERVAL
        ):
            self.cleanup()

            self.last_cleanup = now
    # =====================================
    # GLOBAL ID LIFECYCLE CLEANUP
    # =====================================
    def cleanup(self):

        now = time.time()

        for global_id, track in list(
                self.global_tracks.items()
        ):

            age = (
                    now -
                    track["last_seen"]
            )

            status = track.get(
                "status",
                "active"
            )

            # =================================
            # ACTIVE → LOST
            # =================================

            if (
                    status == "active"
                    and
                    age > self.REGISTRY_TIMEOUT
            ):

                track["status"] = "lost"

                track["lost_at"] = now

                print(
                    "[GLOBAL TRACK LOST]",
                    f"global_id={global_id}",
                    f"last_camera={track['last_camera']}"
                )

            # =================================
            # LOST → EXPIRED
            # =================================

            elif (
                    status == "lost"
                    and
                    track.get("lost_at") is not None
                    and
                    now - track["lost_at"]
                    > self.REGISTRY_TIMEOUT
            ):

                track["status"] = "expired"

                track["expired_at"] = now

                print(
                    "[GLOBAL TRACK EXPIRED]",
                    f"global_id={global_id}"
                )

    # =====================================
    # SUMMARY
    # =====================================
    def get_summary(self):

        active = 0
        lost = 0
        expired = 0

        for track in self.global_tracks.values():

            status = track.get(
                "status",
                "active"
            )

            if status == "active":
                active += 1

            elif status == "lost":
                lost += 1

            elif status == "expired":
                expired += 1

        return {

            "total_global_tracks":
                len(self.global_tracks),

            "total_local_mappings":
                len(self.track_map),

            "active_tracks":
                active,

            "lost_tracks":
                lost,

            "expired_tracks":
                expired,

            "tracks":
                list(
                    self.global_tracks.values()
                )
        }

# =====================================
# GLOBAL SINGLETON
# =====================================

global_registry = GlobalTrackRegistry()
