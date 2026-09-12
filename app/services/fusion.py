# app/services/fusion.py

from app.services.analytics import analytics
from app.services.crowd_metrics import crowd_metrics
from app.services.zones import zones
from app.services.line import line_manager
from app.services.heatmap import heatmap
from app.services.speed import speed
from app.services.trajectory import trajectory
from app.services.loitering import loitering
from app.services.uturn import uturn
from app.services.congestion import congestion
from app.services.groups import groups
from app.services.abnormal import abnormal
from app.services.restricted_zone import restricted_zone
from app.services.prediction import prediction
from app.services.congestion_forecast import congestion_forecast
from app.services.queue_prediction import (queue_prediction)
from app.services.flow_forecast import flow_forecast
from app.services.route_prediction import route_prediction
from app.services.camera_manager import (camera_manager)
from app.services.synchronization import (synchronization)
from app.services.global_registry import global_registry
from app.services.reid import reid
from app.services.handoff import handoff
from app.services.reid_matcher import (reid_matcher)
from app.services.merge_engine import merge_engine
from app.services.multi_camera_forecast import (MultiCameraForecast)

class FusionEngine:
    """
    SINGLE SOURCE OF TRUTH (Production CCTV Brain)

    Fusion coordinates all analytics services.
    It performs NO analytics calculations itself.
    """

    def __init__(
        self,
        analytics,
        crowd_metrics,
        zones,
        line_manager
    ):

        self.analytics = analytics
        self.crowd_metrics = crowd_metrics
        self.zones = zones
        self.line_manager = line_manager
        self.heatmap = heatmap
        self.speed = speed
        self.trajectory = trajectory
        self.loitering = loitering
        self.uturn = uturn
        self.congestion = congestion
        self.groups = groups
        self.abnormal = abnormal
        self.restricted_zone = restricted_zone
        self.prediction = prediction
        self.congestion_forecast = congestion_forecast
        self.queue_prediction = queue_prediction
        self.flow_forecast = flow_forecast
        self.route_prediction = route_prediction
        self.camera_manager = camera_manager
        self.synchronization = synchronization
        self.global_registry = global_registry
        self.reid = reid
        self.reid_matcher = reid_matcher
        self.handoff = handoff

        self.multi_camera_forecast = (
            MultiCameraForecast(
                handoff=self.handoff,
                global_registry=self.global_registry
            )
        )


        # live frame state
        self.active_tracks_frame = set()
        self.last_frame_active = set()

        # future event buffer
        self.events = []

    # =====================================
    # INITIALIZE FRAME SERVICES
    # =====================================
    def initialize_frame(self, frame):
        self.heatmap.initialize(frame.shape)

    # =====================================
    # FRAME RESET
    # =====================================
    def finalize_frame(self):

        # preserve previous frame
        self.last_frame_active = self.active_tracks_frame.copy()

        self.heatmap.decay_heat()

        # finalize per-track analytics
        self.analytics.finalize_frame(
            self.last_frame_active
        )
        self.trajectory.finalize_frame(
            self.last_frame_active
        )

        self.groups.finalize_frame(
            self.last_frame_active
        )

        # update crowd-level analytics
        self.crowd_metrics.update(
            active_tracks=self.last_frame_active,
            entries=self.line_manager.get_counts().get("entry", 0),
            exits=self.line_manager.get_counts().get("exit", 0),
            zones=self.zones.get_counts()
        )

        self.congestion_forecast.update(
            self.zones.get_counts()
        )

        self.queue_prediction.update(
            self.zones.get_counts()
        )

        flow = self.line_manager.get_flow_metrics()

        self.flow_forecast.update(
            flow["entry_rate_per_min"],
            flow["exit_rate_per_min"]
        )

        # prepare next frame
        self.active_tracks_frame.clear()

        self.congestion.update(

            utilization=self.zones.get_utilization(),

            density=self.zones.get_density(),

            occupancy=self.zones.get_counts()
        )

    # =====================================
    # DETECTION UPDATE
    # =====================================
    def update(
            self,
            track_id,
            cx,
            cy,
            global_id=None,
            camera_id="cam_1"
    ):

        if global_id is None:
            global_id = self.global_registry.register_track(
                camera_id=camera_id,
                local_track_id=track_id
            )

        # =====================================
        # GLOBAL CAMERA STATE
        # =====================================
        self.global_registry.update_camera(
            global_id=global_id,
            camera_id=camera_id,
            local_track_id=track_id
        )

        # =====================================
        # CROSS-CAMERA HANDOFF
        # =====================================
        self.handoff.update(
            global_id=global_id,
            camera_id=camera_id
        )

        self.active_tracks_frame.add(track_id)
        self.zones.update(track_id, cx, cy)
        self.line_manager.update(track_id, cx, cy)
        self.analytics.update(track_id)
        self.heatmap.update(cx, cy)
        self.speed.update(track_id, cx, cy)
        self.trajectory.update(track_id, cx, cy)

        current_direction = (
            self.trajectory.get_track_direction(track_id)
        )

        dominant_direction = (
            self.trajectory.get_dominant_direction(track_id)
        )

        self.route_prediction.update(
            track_id,
            current_direction,
            dominant_direction
        )


        current_zone = self.zones.get_track_zone(
            track_id
        )

        if current_zone:
            self.restricted_zone.update(
                global_id,
                camera_id,
                current_zone,
                self.zones.get_restricted_zones()
            )

        direction_changes = (
            self.trajectory.get_direction_changes(
                track_id
            )
        )

        direction = (
            self.trajectory.get_track_direction(
                track_id
            )
        )

        track_speed = (
            self.speed.get_track_speed(
                track_id
            )
        )

        self.abnormal.update(
            track_id,
            track_speed,
            direction,
            direction_changes
        )

        track = self.trajectory.get_track_summary(
            track_id
        )

        self.loitering.update(

            track_id=track_id,

            duration=track["tracking_duration"],

            speed=self.speed.get_track_speed(
                track_id
            ),

            distance=track["distance_travelled"]
        )

        track = self.trajectory.get_track_summary(
            track_id
        )

        self.uturn.update(

            track_id=track_id,

            dominant_direction=track[
                "dominant_direction"
            ],

            current_direction=track[
                "direction"
            ]
        )

        self.groups.update(
            track_id,
            cx,
            cy
        )
    # =====================================
    # DASHBOARD CONTRACT
    # =====================================
    def get_global_stats(self):

        line_counts = self.line_manager.get_counts()

        stats = {
            # -------------------------
            # line analytics
            # -------------------------
            "entries": line_counts.get("entry", 0),
            "exits": line_counts.get("exit", 0),

            # -------------------------
            # live occupancy
            # -------------------------
            "active": max(
                len(self.active_tracks_frame),
                len(self.last_frame_active)
            ),

            # -------------------------
            # GLOBAL OCCUPANCY
            # -------------------------
            "global_occupancy":
                self.get_global_occupancy(),

            "global_occupancy_by_camera":
                self.get_global_occupancy_by_camera(),

            # -------------------------
            # zones
            # -------------------------
            "zones": dict(
                self.zones.get_counts()
            ),

            # -------------------------
            # dwell time
            # -------------------------
            "dwell": self.get_dwell_summary(),

            # -------------------------
            # speed
            # -------------------------
            "speed": self.get_speed_summary(),

            # -------------------------
            # trajectory
            # -------------------------
            "trajectory": self.get_trajectory_summary(),

            # -------------------------
            # prediction
            # -------------------------
            "prediction": self.get_prediction_summary(),
        }

        # merge crowd analytics
        stats.update(
            self.crowd_metrics.get_metrics()
        )

        return stats
    # =====================================
    # DWELL ANALYTICS CONTRACT
    # =====================================
    def get_dwell_summary(self):
        return {
            "average_dwell": self.analytics.get_average_dwell(),
            "maximum_dwell": self.analytics.get_max_dwell(),
            "current_occupancy": self.analytics.get_current_count()
        }

    # =====================================
    # SPEED ANALYTICS CONTRACT
    # =====================================
    def get_speed_summary(self):
        return self.speed.get_speed_summary()

    # =====================================
    # TRAJECTORY ANALYTICS CONTRACT
    # =====================================
    def get_trajectory_summary(self):
        return self.trajectory.get_summary()

    # =====================================
    # ACTIVE TRACKS
    # =====================================
    def get_active_tracks(self):

        tracks = self.active_tracks_frame

        if not tracks:
            tracks = self.last_frame_active

        return sorted(tracks)

    def get_direction_summary(self):
        return self.trajectory.get_direction_summary()

    # =====================================
    # LOITERING ANALYTICS CONTRACT
    # =====================================
    def get_loitering_summary(self):
        return self.loitering.get_summary()

    # =====================================
    # U-TURN ANALYTICS CONTRACT
    # =====================================
    def get_uturn_summary(self):
        return self.uturn.get_summary()

    # =====================================
    # CONGESTION ANALYTICS CONTRACT
    # =====================================
    def get_congestion_summary(self):
        return self.congestion.get_summary()

    # =====================================
    # ABNORMAL ANALYTICS CONTRACT
    # =====================================
    def get_abnormal_summary(self):
        return self.abnormal.get_summary()

    # =====================================
    # RESTRICTED ZONE ANALYTICS
    # =====================================

    def get_restricted_zone_summary(self):

        return self.restricted_zone.get_summary()

    # =====================================
    # OCCUPANCY FORECAST
    # =====================================

    def get_prediction_summary(self):

        return self.prediction.get_prediction(
            self.crowd_metrics.get_history()
        )

    # =====================================
    # MULTI-CAMERA FORECAST
    # =====================================

    def get_multi_camera_forecast(
            self,
            lookback_seconds=300
    ):
        return self.multi_camera_forecast.get_summary(
            lookback_seconds=lookback_seconds
        )

    # =====================================
    # ROUTE PREDICTION
    # =====================================
    def get_route_predictions(self):

        return self.route_prediction.get_summary()

    def get_track_prediction(
            self,
            track_id
    ):

        return self.route_prediction.get_track_prediction(
            track_id
        )

    # =====================================
    # CAMERA MANAGER
    # =====================================
    def get_camera_summary(self):

        return self.camera_manager.get_summary()

    # =====================================
    # CAMERA ROUTE PREDICTION
    # =====================================

    def get_camera_route_prediction(
            self,
            camera_id
    ):

        return self.handoff.get_most_likely_next_camera(
            camera_id
        )

    # =====================================
    # SYNCHRONIZATION
    # =====================================
    def get_synchronization_summary(self):

        return self.synchronization.get_summary()

    # =====================================
    # GLOBAL TRACK REGISTRY
    # =====================================
    def get_global_registry_summary(self):

        return self.global_registry.get_summary()

    # =====================================
    # GLOBAL ID ROUTE PREDICTION
    # =====================================

    def get_global_id_route_prediction(
            self,
            global_id
    ):

        # ---------------------------------
        # GET GLOBAL IDENTITY
        # ---------------------------------

        track = self.global_registry.get_track(
            global_id
        )

        # ---------------------------------
        # UNKNOWN GLOBAL ID
        # ---------------------------------

        if track is None:

            return {

                "global_id": global_id,

                "current_camera": None,

                "predicted_camera": None,

                "confidence": 0.0,

                "known_routes": 0
            }

        # ---------------------------------
        # CURRENT CAMERA
        # ---------------------------------

        current_camera = track.get(
            "current_camera"
        )

        # ---------------------------------
        # GET ROUTE PREDICTION
        #
        # handoff is the existing
        # camera-route learning source.
        # ---------------------------------

        prediction = (
            self.handoff
            .get_global_id_route_prediction(
                global_id
            )
        )

        # ---------------------------------
        # SAFETY FALLBACK
        # ---------------------------------

        if prediction is None:

            prediction = {

                "predicted_camera": None,

                "confidence": 0.0,

                "known_routes": 0
            }

        # ---------------------------------
        # UNIFIED PRODUCTION CONTRACT
        # ---------------------------------

        return {

            "global_id": global_id,

            "current_camera":
                current_camera,

            "predicted_camera":
                prediction.get(
                    "predicted_camera"
                ),

            "confidence":
                prediction.get(
                    "confidence",
                    0.0
                ),

            "known_routes":
                prediction.get(
                    "known_routes",
                    0
                )
        }

    # =====================================
    # GLOBAL OCCUPANCY
    # =====================================

    def get_global_occupancy(self):

        occupancy = 0

        for track in self.global_registry.global_tracks.values():

            if track.get("status") == "active":
                occupancy += 1

        return occupancy

    # =====================================
    # GLOBAL OCCUPANCY BY CAMERA
    # =====================================

    def get_global_occupancy_by_camera(self):

        occupancy = {}

        for track in self.global_registry.global_tracks.values():

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
    # GLOBAL OCCUPANCY CONTRACT
    # =====================================

    def get_global_occupancy_summary(self):

        return {
            "global_occupancy":
                self.get_global_occupancy(),

            "occupancy_by_camera":
                self.get_global_occupancy_by_camera()
        }

    # =====================================
    # GLOBAL OCCUPANCY
    # =====================================
    def get_global_occupancy(self):

        return self.global_registry.get_global_occupancy()

    # =====================================
    # GLOBAL OCCUPANCY BY CAMERA
    # =====================================
    def get_global_occupancy_by_camera(self):

        return self.global_registry.get_global_occupancy_by_camera()

    # =====================================
    # GLOBAL ID LOOKUP
    # =====================================

    def get_global_id(
            self,
            camera_id,
            local_track_id
    ):

        return self.global_registry.get_global_id(
            camera_id,
            local_track_id
        )

    # =====================================
    # GLOBAL ID REACTIVATION
    # =====================================
    def reactivate_global_id(
            self,
            global_id,
            camera_id,
            local_track_id
    ):

        return self.global_registry.reactivate_track(
            global_id=global_id,
            camera_id=camera_id,
            local_track_id=local_track_id
        )

    # =====================================
    # REID SUMMARY
    # =====================================
    def get_reid_summary(self):

        return self.reid.get_summary()

    # =====================================
    # REID MATCHES
    # =====================================
    def get_reid_matches(self):

        return self.reid_matcher.get_summary()

    # =====================================
    # MERGE SUMMARY
    # =====================================

    def get_merge_summary(self):

        return merge_engine.get_summary()

    # =====================================
    # HANDOFF SUMMARY
    # =====================================
    def get_handoff_summary(self):

        return self.handoff.get_summary()

    # =====================================
    # GLOBAL ID ROUTE PREDICTION
    # =====================================

    def get_global_id_route_prediction(
            self,
            global_id
    ):

        return self.handoff.get_global_id_route_prediction(
            global_id
        )

    # =====================================
    # CAMERA ROUTE LEARNING
    # =====================================

    def get_camera_route_summary(self):

        return self.handoff.get_route_summary()


    # =====================================
    # CAMERA ROUTE STATISTICS
    # =====================================

    def get_camera_route_statistics(self):

        return self.handoff.get_route_statistics()

    # =====================================
    # CAMERA ROUTE CONFIDENCE
    # =====================================

    def get_camera_route_confidence(self):

        return self.handoff.get_route_confidence()

    # =====================================
    # MOST LIKELY NEXT CAMERA
    # =====================================

    def get_most_likely_next_camera(
            self,
            current_camera
    ):

        return self.handoff.get_most_likely_next_camera(
            current_camera
        )

    # =====================================
    # CAMERA ROUTE PREDICTION
    # =====================================

    def get_camera_route_prediction(
            self,
            camera_id
    ):

        return self.handoff.get_most_likely_next_camera(
            camera_id
        )

    # =====================================
    # GLOBAL ID ROUTE PREDICTION
    # =====================================

    def get_global_id_route_prediction(
            self,
            global_id
    ):

        return self.handoff.get_global_id_route_prediction(
            global_id
        )

    # =====================================
    # CONGESTION FORECAST
    # =====================================
    def get_congestion_forecast(self):

        return self.congestion_forecast.get_summary()

    # =====================================
    # QUEUE PREDICTION
    # =====================================
    def get_queue_prediction(self):

        return self.queue_prediction.get_summary()

    # =====================================
    # FLOW FORECAST
    # =====================================
    def get_flow_forecast(self):

        return self.flow_forecast.get_summary()

    # =====================================
    # GROUP SUMMARY
    # =====================================

    def get_group_summary(self):
        return self.groups.get_summary()

    # =====================================
    # TRACK SUMMARY
    # =====================================

    def get_track_summary(self, track_id):
        # ---------------------------------
        # Trajectory Analytics
        # ---------------------------------
        track = self.trajectory.get_track_summary(track_id)

        # ---------------------------------
        # Merge analytics from other services
        # ---------------------------------
        track.update({

            # Current frame state
            "active": (
                    track_id in self.active_tracks_frame
            ),

            # Analytics lifecycle state
            "currently_tracked": (
                    track_id in self.analytics.current_active
            ),

            # Speed Analytics
            "speed": round(
                self.speed.get_track_speed(track_id),
                2
            ),

            "loitering": self.loitering.is_loitering(
                track_id
            ),

            "uturn": self.uturn.is_uturn(
                track_id
            ),

            "restricted_zone_violation":
                self.restricted_zone.is_violating(
                    track_id
                ),

        })

        track.update(
            self.groups.get_track_group(
                track_id
            )
        )

        track.update(
            self.abnormal.get_track_status(
                track_id
            )
        )

        return track


# =====================================
# GLOBAL SINGLETON
# =====================================

fusion = FusionEngine(
    analytics=analytics,
    crowd_metrics=crowd_metrics,
    zones=zones,
    line_manager=line_manager
)

