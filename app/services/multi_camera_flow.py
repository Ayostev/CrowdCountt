# app/services/multi_camera_flow.py

from collections import defaultdict


class MultiCameraFlow:
    """
    Multi-Camera Flow Intelligence

    Responsibilities
    ----------------
    • Aggregate confirmed cross-camera transitions
    • Calculate camera inflow
    • Calculate camera outflow
    • Calculate camera net flow
    • Provide route-level flow statistics
    • Classify camera flow roles
    • Identify dominant routes
    • Identify source and destination cameras
    • Provide network-level flow interpretation
    • Provide a unified multi-camera flow summary

    IMPORTANT
    ---------
    This service does NOT create its own camera-transition state.

    The authoritative source of cross-camera movement is:

        HandoffTracker.route_transitions

    Therefore this service consumes existing handoff state
    instead of maintaining a second competing source of truth.
    """

    def __init__(self, handoff):

        self.handoff = handoff

    # =====================================
    # ROUTE TRANSITIONS
    # =====================================

    def get_route_transitions(self):

        return list(
            self.handoff.route_transitions
        )

    # =====================================
    # ROUTE FLOW AGGREGATION
    # =====================================

    def get_route_flow(self):

        route_flow = (
            self.handoff.get_route_statistics()
        )

        routes = list(
            route_flow["routes"]
        )

        # ---------------------------------
        # SORT BY FLOW VOLUME
        # ---------------------------------

        routes.sort(
            key=lambda route:
            route["transitions"],
            reverse=True
        )

        return {

            "total_routes":
                route_flow[
                    "total_routes"
                ],

            "total_transitions":
                route_flow[
                    "total_transitions"
                ],

            "routes":
                routes
        }
    # =====================================
    # CAMERA INFLOW
    # =====================================

    def get_camera_inflow(self):

        inflow = defaultdict(int)

        for transition in (
            self.get_route_transitions()
        ):

            to_camera = transition.get(
                "to_camera"
            )

            if to_camera is None:
                continue

            inflow[
                to_camera
            ] += 1

        return dict(inflow)

    # =====================================
    # CAMERA OUTFLOW
    # =====================================

    def get_camera_outflow(self):

        outflow = defaultdict(int)

        for transition in (
            self.get_route_transitions()
        ):

            from_camera = transition.get(
                "from_camera"
            )

            if from_camera is None:
                continue

            outflow[
                from_camera
            ] += 1

        return dict(outflow)

    # =====================================
    # CAMERA NET FLOW
    # =====================================

    def get_camera_net_flow(self):

        inflow = (
            self.get_camera_inflow()
        )

        outflow = (
            self.get_camera_outflow()
        )

        cameras = set(
            inflow.keys()
        ).union(
            outflow.keys()
        )

        net_flow = {}

        for camera_id in cameras:

            net_flow[camera_id] = (
                inflow.get(
                    camera_id,
                    0
                )
                -
                outflow.get(
                    camera_id,
                    0
                )
            )

        return dict(
            sorted(
                net_flow.items(),
                key=lambda item:
                    item[1],
                reverse=True
            )
        )

    # =====================================
    # CAMERA FLOW SUMMARY
    # =====================================

    def get_camera_flow_summary(self):

        inflow = (
            self.get_camera_inflow()
        )

        outflow = (
            self.get_camera_outflow()
        )

        net_flow = (
            self.get_camera_net_flow()
        )

        cameras = set(
            inflow.keys()
        ).union(
            outflow.keys()
        )

        summary = {}

        for camera_id in cameras:

            camera_inflow = inflow.get(
                camera_id,
                0
            )

            camera_outflow = outflow.get(
                camera_id,
                0
            )

            camera_net_flow = net_flow.get(
                camera_id,
                0
            )

            # ---------------------------------
            # CLASSIFY CAMERA ROLE
            # ---------------------------------

            if (
                camera_outflow > 0
                and
                camera_inflow == 0
            ):

                role = "SOURCE"

            elif (
                camera_inflow > 0
                and
                camera_outflow == 0
            ):

                role = "DESTINATION"

            elif (
                camera_inflow > 0
                and
                camera_outflow > 0
                and
                camera_net_flow == 0
            ):

                role = "BALANCED"

            elif (
                camera_inflow > 0
                and
                camera_outflow > 0
            ):

                role = "INTERMEDIATE"

            else:

                role = "UNCLASSIFIED"

            summary[camera_id] = {

                "inflow":
                    camera_inflow,

                "outflow":
                    camera_outflow,

                "net_flow":
                    camera_net_flow,

                "role":
                    role
            }

        return summary

    # =====================================
    # DOMINANT ROUTE
    # =====================================

    def get_dominant_route(self):

        route_flow = (
            self.get_route_flow()
        )

        routes = route_flow[
            "routes"
        ]

        if not routes:

            return None

        return routes[0]

    # =====================================
    # SOURCE CAMERAS
    # =====================================

    def get_source_cameras(self):

        summary = (
            self.get_camera_flow_summary()
        )

        return [

            camera_id

            for camera_id, data
            in summary.items()

            if data["role"] == "SOURCE"
        ]

    # =====================================
    # DESTINATION CAMERAS
    # =====================================

    def get_destination_cameras(self):

        summary = (
            self.get_camera_flow_summary()
        )

        return [

            camera_id

            for camera_id, data
            in summary.items()

            if data["role"] == "DESTINATION"
        ]

    # =====================================
    # INTERMEDIATE CAMERAS
    # =====================================

    def get_intermediate_cameras(self):

        summary = (
            self.get_camera_flow_summary()
        )

        return [

            camera_id

            for camera_id, data
            in summary.items()

            if data["role"] == "INTERMEDIATE"
        ]

    # =====================================
    # BALANCED CAMERAS
    # =====================================

    def get_balanced_cameras(self):

        summary = (
            self.get_camera_flow_summary()
        )

        return [

            camera_id

            for camera_id, data
            in summary.items()

            if data["role"] == "BALANCED"
        ]

    # =====================================
    # NETWORK FLOW INTERPRETATION
    # =====================================

    def get_network_interpretation(self):

        route_flow = (
            self.get_route_flow()
        )

        camera_summary = (
            self.get_camera_flow_summary()
        )

        dominant_route = (
            self.get_dominant_route()
        )

        source_cameras = (
            self.get_source_cameras()
        )

        destination_cameras = (
            self.get_destination_cameras()
        )

        intermediate_cameras = (
            self.get_intermediate_cameras()
        )

        balanced_cameras = (
            self.get_balanced_cameras()
        )

        # ---------------------------------
        # NETWORK STATUS
        # ---------------------------------

        if route_flow["total_transitions"] == 0:

            network_status = "NO_FLOW"

        elif source_cameras and destination_cameras:

            network_status = "ACTIVE_NETWORK"

        else:

            network_status = "ACTIVE_FLOW"

        # ---------------------------------
        # BUSIEST SOURCE
        # ---------------------------------

        busiest_source = None

        if source_cameras:

            busiest_source = max(

                source_cameras,

                key=lambda camera_id:
                    camera_summary[
                        camera_id
                    ]["outflow"]
            )

        # ---------------------------------
        # BUSIEST DESTINATION
        # ---------------------------------

        busiest_destination = None

        if destination_cameras:

            busiest_destination = max(

                destination_cameras,

                key=lambda camera_id:
                    camera_summary[
                        camera_id
                    ]["inflow"]
            )

        return {

            "network_status":
                network_status,

            "total_transitions":
                route_flow[
                    "total_transitions"
                ],

            "total_routes":
                route_flow[
                    "total_routes"
                ],

            "dominant_route":
                dominant_route,

            "source_cameras":
                source_cameras,

            "destination_cameras":
                destination_cameras,

            "intermediate_cameras":
                intermediate_cameras,

            "balanced_cameras":
                balanced_cameras,

            "busiest_source":
                busiest_source,

            "busiest_destination":
                busiest_destination
        }

    # =====================================
    # NETWORK FLOW SUMMARY
    # =====================================

    def get_summary(self):

        route_flow = (
            self.get_route_flow()
        )

        camera_inflow = (
            self.get_camera_inflow()
        )

        camera_outflow = (
            self.get_camera_outflow()
        )

        camera_net_flow = (
            self.get_camera_net_flow()
        )

        camera_flow = (
            self.get_camera_flow_summary()
        )

        interpretation = (
            self.get_network_interpretation()
        )

        return {

            "total_transitions":
                route_flow[
                    "total_transitions"
                ],

            "total_routes":
                route_flow[
                    "total_routes"
                ],

            "camera_inflow":
                camera_inflow,

            "camera_outflow":
                camera_outflow,

            "camera_net_flow":
                camera_net_flow,

            "camera_flow":
                camera_flow,

            "routes":
                route_flow[
                    "routes"
                ],

            "interpretation":
                interpretation
        }


# =====================================
# GLOBAL SINGLETON
# =====================================

from app.services.handoff import handoff


multi_camera_flow = MultiCameraFlow(
    handoff
)

