# app/services/multi_camera_forecast.py

import time
from collections import defaultdict


class MultiCameraForecast:
    """
    Multi-Camera Forecasting Engine

    Responsibilities
    ----------------
    - Forecast camera-level occupancy
    - Forecast camera inflow
    - Forecast camera outflow
    - Forecast camera net flow
    - Forecast camera-to-camera transition volumes
    - Provide network-level forecast
    - Provide forecast confidence

    IMPORTANT
    ---------
    This service does NOT maintain a second transition history.

    Authoritative transition history remains:

        HandoffTracker.route_transitions

    Current camera occupancy remains sourced from:

        GlobalTrackRegistry
    """

    DEFAULT_LOOKBACK_SECONDS = 300

    FORECAST_HORIZONS = (
        30,
        60,
        300,
    )

    def __init__(self, handoff, global_registry):
        self.handoff = handoff
        self.global_registry = global_registry

    # =====================================
    # CURRENT OCCUPANCY
    # =====================================

    def get_current_occupancy(self):
        return dict(
            self.global_registry.get_global_occupancy_by_camera()
        )

    # =====================================
    # RECENT TRANSITIONS
    # =====================================

    def get_recent_transitions(
        self,
        lookback_seconds=None,
        now=None
    ):
        if lookback_seconds is None:
            lookback_seconds = self.DEFAULT_LOOKBACK_SECONDS

        if now is None:
            now = time.time()

        cutoff = now - lookback_seconds

        transitions = []

        for transition in self.handoff.route_transitions:

            timestamp = transition.get("timestamp")

            if timestamp is None:
                continue

            if timestamp < cutoff:
                continue

            from_camera = transition.get(
                "from_camera"
            )

            to_camera = transition.get(
                "to_camera"
            )

            if not from_camera or not to_camera:
                continue

            transitions.append(
                transition
            )

        return transitions

    # =====================================
    # ROUTE COUNTS
    # =====================================

    def get_route_counts(
        self,
        lookback_seconds=None,
        now=None
    ):
        transitions = self.get_recent_transitions(
            lookback_seconds=lookback_seconds,
            now=now
        )

        counts = defaultdict(int)

        for transition in transitions:

            key = (
                transition["from_camera"],
                transition["to_camera"]
            )

            counts[key] += 1

        return dict(counts)

    # =====================================
    # ROUTE FORECAST
    # =====================================

    def get_route_forecast(
        self,
        horizon_seconds=60,
        lookback_seconds=None,
        now=None
    ):
        if lookback_seconds is None:
            lookback_seconds = (
                self.DEFAULT_LOOKBACK_SECONDS
            )

        if now is None:
            now = time.time()

        route_counts = self.get_route_counts(
            lookback_seconds=lookback_seconds,
            now=now
        )

        route_forecasts = []

        minutes = (
            lookback_seconds / 60.0
        )

        if minutes <= 0:
            minutes = 1.0

        for (
            from_camera,
            to_camera
        ), transitions in route_counts.items():

            rate_per_min = (
                transitions / minutes
            )

            predicted = (
                rate_per_min
                * (horizon_seconds / 60.0)
            )

            route_forecasts.append({
                "from_camera": from_camera,
                "to_camera": to_camera,
                "transitions_observed": transitions,
                "rate_per_min": round(
                    rate_per_min,
                    3
                ),
                "predicted_transitions": round(
                    predicted,
                    2
                )
            })

        route_forecasts.sort(
            key=lambda item:
                item["predicted_transitions"],
            reverse=True
        )

        return route_forecasts

    # =====================================
    # CAMERA FLOW FORECAST
    # =====================================

    def get_camera_flow_forecast(
        self,
        horizon_seconds=60,
        lookback_seconds=None,
        now=None
    ):
        if lookback_seconds is None:
            lookback_seconds = (
                self.DEFAULT_LOOKBACK_SECONDS
            )

        if now is None:
            now = time.time()

        transitions = self.get_recent_transitions(
            lookback_seconds=lookback_seconds,
            now=now
        )

        minutes = (
            lookback_seconds / 60.0
        )

        if minutes <= 0:
            minutes = 1.0

        inflow_counts = defaultdict(int)
        outflow_counts = defaultdict(int)

        for transition in transitions:

            from_camera = transition.get(
                "from_camera"
            )

            to_camera = transition.get(
                "to_camera"
            )

            if from_camera:
                outflow_counts[
                    from_camera
                ] += 1

            if to_camera:
                inflow_counts[
                    to_camera
                ] += 1

        cameras = set(
            self.get_current_occupancy().keys()
        )

        cameras.update(
            inflow_counts.keys()
        )

        cameras.update(
            outflow_counts.keys()
        )

        result = {}

        for camera_id in cameras:

            inflow_rate = (
                inflow_counts.get(
                    camera_id,
                    0
                ) / minutes
            )

            outflow_rate = (
                outflow_counts.get(
                    camera_id,
                    0
                ) / minutes
            )

            net_rate = (
                inflow_rate
                - outflow_rate
            )

            current_occupancy = (
                self.get_current_occupancy().get(
                    camera_id,
                    0
                )
            )

            projected_change = (
                net_rate
                * (horizon_seconds / 60.0)
            )

            predicted_occupancy = max(
                0,
                current_occupancy
                + projected_change
            )

            if net_rate > 0.05:
                trend = "INCREASING"
            elif net_rate < -0.05:
                trend = "DECREASING"
            else:
                trend = "STABLE"

            result[camera_id] = {
                "current_occupancy":
                    current_occupancy,

                "inflow_rate_per_min":
                    round(
                        inflow_rate,
                        3
                    ),

                "outflow_rate_per_min":
                    round(
                        outflow_rate,
                        3
                    ),

                "net_flow_rate_per_min":
                    round(
                        net_rate,
                        3
                    ),

                "predicted_occupancy":
                    round(
                        predicted_occupancy,
                        2
                    ),

                "trend":
                    trend
            }

        return result

    # =====================================
    # FORECAST CONFIDENCE
    # =====================================

    def get_forecast_confidence(
        self,
        transitions_observed
    ):
        """
        Confidence based on observed transition volume.

        This is an empirical data-confidence score,
        not an ML probability.
        """

        if transitions_observed <= 0:
            return 0.0

        if transitions_observed >= 50:
            return 0.95

        if transitions_observed >= 25:
            return 0.85

        if transitions_observed >= 10:
            return 0.70

        if transitions_observed >= 5:
            return 0.50

        return 0.30

    # =====================================
    # NETWORK FORECAST
    # =====================================

    def get_network_forecast(
        self,
        lookback_seconds=None,
        now=None
    ):
        if lookback_seconds is None:
            lookback_seconds = (
                self.DEFAULT_LOOKBACK_SECONDS
            )

        if now is None:
            now = time.time()

        horizons = {}

        for horizon in self.FORECAST_HORIZONS:

            camera_flow = (
                self.get_camera_flow_forecast(
                    horizon_seconds=horizon,
                    lookback_seconds=lookback_seconds,
                    now=now
                )
            )

            route_forecast = (
                self.get_route_forecast(
                    horizon_seconds=horizon,
                    lookback_seconds=lookback_seconds,
                    now=now
                )
            )

            horizons[
                f"{horizon}s"
            ] = {
                "camera_forecast":
                    camera_flow,
                "route_forecast":
                    route_forecast
            }

        dominant_route = None

        route_60s = horizons["60s"][
            "route_forecast"
        ]

        if route_60s:

            dominant = route_60s[0]

            dominant_route = {
                **dominant,
                "confidence":
                    self.get_forecast_confidence(
                        dominant[
                            "transitions_observed"
                        ]
                    )
            }

        total_routes = len(
            self.handoff.route_transitions
        )

        if total_routes == 0:
            network_status = "NO_FLOW"
        else:
            network_status = "ACTIVE_NETWORK"

        return {
            "lookback_seconds":
                lookback_seconds,

            "forecast_horizons":
                horizons,

            "dominant_predicted_route":
                dominant_route,

            "network_status":
                network_status,

            "observed_transition_count":
                total_routes
        }

    # =====================================
    # SUMMARY
    # =====================================

    def get_summary(
        self,
        lookback_seconds=None,
        now=None
    ):
        return self.get_network_forecast(
            lookback_seconds=lookback_seconds,
            now=now
        )


# =====================================
# FACTORY
# =====================================

def create_multi_camera_forecast(
    handoff,
    global_registry
):
    return MultiCameraForecast(
        handoff=handoff,
        global_registry=global_registry
    )
