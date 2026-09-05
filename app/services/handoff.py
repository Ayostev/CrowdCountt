# app/services/handoff.py

import time


class HandoffTracker:
    """
    Cross-Camera Handoff Tracking

    Responsibilities
    ----------------
    • Record confirmed global-identity movement between cameras
    • Maintain last known camera per global ID
    • Maintain authoritative camera-transition history
    • Provide handoff history and route summaries
    • Provide route confidence and next-camera prediction

    Identity Contract
    -----------------
    Handoff identity is based on global_id,
    NOT local track_id.

    Transition Contract
    -------------------
    A route transition is created only when a known
    global_id is observed in a different camera from
    its previously recorded camera.

    Authoritative State
    -------------------
    route_transitions is the single authoritative
    source of confirmed cross-camera transitions.

    MultiCameraFlow consumes this state and does not
    maintain a competing transition history.
    """

    def __init__(self):

        # ---------------------------------
        # HANDOFF HISTORY
        # ---------------------------------

        self.handoffs = []

        # ---------------------------------
        # AUTHORITATIVE ROUTE TRANSITIONS
        # ---------------------------------

        self.route_transitions = []

        # ---------------------------------
        # LAST KNOWN CAMERA
        #
        # global_id -> camera_id
        # ---------------------------------

        self.last_camera = {}

        # ---------------------------------
        # INTEGRITY COUNTERS
        # ---------------------------------

        self.invalid_observations = 0

    # =====================================
    # OBSERVATION VALIDATION
    # =====================================

    @staticmethod
    def _valid_global_id(global_id):

        return (
            global_id is not None
            and
            isinstance(global_id, int)
            and
            global_id >= 0
        )

    @staticmethod
    def _valid_camera_id(camera_id):

        return (
            camera_id is not None
            and
            isinstance(camera_id, str)
            and
            camera_id.strip() != ""
        )

    # =====================================
    # UPDATE CAMERA PRESENCE
    # =====================================

    def update(
        self,
        global_id,
        camera_id
    ):
        """
        Register the current camera observation
        for a global identity.

        Returns
        -------
        dict or None

        None:
            No transition occurred.

        dict:
            A confirmed camera transition.
        """

        # =================================
        # VALIDATE OBSERVATION
        # =================================

        if not self._valid_global_id(global_id):

            self.invalid_observations += 1

            return None

        if not self._valid_camera_id(camera_id):

            self.invalid_observations += 1

            return None

        camera_id = camera_id.strip()

        # =================================
        # FIRST OBSERVATION
        # =================================

        previous_camera = self.last_camera.get(
            global_id
        )

        if previous_camera is None:

            self.last_camera[
                global_id
            ] = camera_id

            return None

        # =================================
        # SAME CAMERA
        # =================================

        if previous_camera == camera_id:

            return None

        # =================================
        # CONFIRMED CAMERA TRANSITION
        # =================================

        timestamp = time.time()

        transition = {

            "global_id":
                global_id,

            "from_camera":
                previous_camera,

            "to_camera":
                camera_id,

            "timestamp":
                timestamp
        }

        # ---------------------------------
        # AUTHORITATIVE TRANSITION HISTORY
        # ---------------------------------

        self.route_transitions.append(
            transition
        )

        # ---------------------------------
        # HANDOFF HISTORY
        #
        # Keep the same event information.
        # ---------------------------------

        self.handoffs.append(
            transition.copy()
        )

        # ---------------------------------
        # UPDATE LAST CAMERA
        # ---------------------------------

        self.last_camera[
            global_id
        ] = camera_id

        return transition

    # =====================================
    # SUMMARY
    # =====================================

    def get_summary(self):

        return {

            "total_handoffs":
                len(self.handoffs),

            "handoffs":
                self.handoffs[-100:],

            "invalid_observations":
                self.invalid_observations
        }

    # =====================================
    # CAMERA ROUTE TRANSITIONS
    # =====================================

    def get_route_summary(self):

        return {

            "total_transitions":
                len(
                    self.route_transitions
                ),

            "transitions":
                self.route_transitions[-100:]
        }

    # =====================================
    # ROUTE AGGREGATION
    # =====================================

    def get_route_statistics(self):

        route_counts = {}

        for transition in self.route_transitions:

            from_camera = transition.get(
                "from_camera"
            )

            to_camera = transition.get(
                "to_camera"
            )

            if (
                from_camera is None
                or
                to_camera is None
            ):
                continue

            route_key = (
                from_camera,
                to_camera
            )

            if route_key not in route_counts:

                route_counts[
                    route_key
                ] = 0

            route_counts[
                route_key
            ] += 1

        routes = []

        for (
            route_key,
            count
        ) in route_counts.items():

            routes.append({

                "from_camera":
                    route_key[0],

                "to_camera":
                    route_key[1],

                "transitions":
                    count
            })

        return {

            "total_routes":
                len(routes),

            "total_transitions":
                len(
                    self.route_transitions
                ),

            "routes":
                routes
        }

    # =====================================
    # ROUTE CONFIDENCE
    # =====================================

    def get_route_confidence(self):

        route_counts = {}

        for transition in self.route_transitions:

            from_camera = transition.get(
                "from_camera"
            )

            to_camera = transition.get(
                "to_camera"
            )

            if (
                from_camera is None
                or
                to_camera is None
            ):
                continue

            if (
                from_camera
                not in route_counts
            ):

                route_counts[
                    from_camera
                ] = {}

            if (
                to_camera
                not in route_counts[
                    from_camera
                ]
            ):

                route_counts[
                    from_camera
                ][to_camera] = 0

            route_counts[
                from_camera
            ][to_camera] += 1

        routes = []

        for (
            from_camera,
            destinations
        ) in route_counts.items():

            total_transitions = sum(
                destinations.values()
            )

            if total_transitions <= 0:
                continue

            for (
                to_camera,
                count
            ) in destinations.items():

                confidence = (
                    count /
                    total_transitions
                )

                routes.append({

                    "from_camera":
                        from_camera,

                    "to_camera":
                        to_camera,

                    "transitions":
                        count,

                    "source_transitions":
                        total_transitions,

                    "confidence":
                        round(
                            confidence,
                            4
                        )
                })

        return {

            "total_routes":
                len(routes),

            "routes":
                routes
        }

    # =====================================
    # MOST LIKELY NEXT CAMERA
    # =====================================

    def get_most_likely_next_camera(
        self,
        current_camera
    ):

        route_confidence = (
            self.get_route_confidence()
        )

        candidates = []

        for route in (
            route_confidence["routes"]
        ):

            if (
                route["from_camera"]
                != current_camera
            ):
                continue

            candidates.append(route)

        # ---------------------------------
        # NO KNOWN ROUTE
        # ---------------------------------

        if not candidates:

            return {

                "current_camera":
                    current_camera,

                "predicted_camera":
                    None,

                "confidence":
                    0.0,

                "known_routes":
                    0
            }

        # ---------------------------------
        # STRONGEST ROUTE
        # ---------------------------------

        best_route = max(
            candidates,
            key=lambda route:
                (
                    route["confidence"],
                    route["transitions"]
                )
        )

        return {

            "current_camera":
                current_camera,

            "predicted_camera":
                best_route[
                    "to_camera"
                ],

            "confidence":
                best_route[
                    "confidence"
                ],

            "transitions":
                best_route[
                    "transitions"
                ],

            "known_routes":
                len(candidates)
        }

    # =====================================
    # GLOBAL ID ROUTE PREDICTION
    # =====================================

    def get_global_id_route_prediction(
        self,
        global_id
    ):

        current_camera = (
            self.last_camera.get(
                global_id
            )
        )

        # ---------------------------------
        # GLOBAL ID UNKNOWN
        # ---------------------------------

        if current_camera is None:

            return {

                "global_id":
                    global_id,

                "current_camera":
                    None,

                "predicted_camera":
                    None,

                "confidence":
                    0.0,

                "known_routes":
                    0
            }

        # ---------------------------------
        # PREDICT NEXT CAMERA
        # ---------------------------------

        prediction = (
            self.get_most_likely_next_camera(
                current_camera
            )
        )

        return {

            "global_id":
                global_id,

            "current_camera":
                current_camera,

            "predicted_camera":
                prediction[
                    "predicted_camera"
                ],

            "confidence":
                prediction[
                    "confidence"
                ],

            "transitions":
                prediction.get(
                    "transitions",
                    0
                ),

            "known_routes":
                prediction.get(
                    "known_routes",
                    0
                )
        }


# =====================================
# GLOBAL SINGLETON
# =====================================

handoff = HandoffTracker()