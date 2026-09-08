from fastapi import APIRouter
from app.services.handoff import HandoffTracker
from app.services.global_registry import GlobalTrackRegistry
from app.services.multi_camera_forecast import MultiCameraForecast
from app.services.fusion import fusion
import time

router = APIRouter(
    prefix="/api",
    tags=["Camera Route Intelligence"]
)


# =====================================
# MULTI-CAMERA FLOW PRODUCTION INTEGRATION
# =====================================

@router.get("/test/multi-camera-flow-production")
def test_multi_camera_flow_production():

    # =====================================
    # PRODUCTION SINGLETONS
    # =====================================

    from app.services.handoff import handoff
    from app.services.multi_camera_flow import multi_camera_flow

    # =====================================
    # CREATE A FRESH CONTROLLED TEST
    #
    # IMPORTANT:
    # We temporarily clear the production
    # handoff route state so this test is
    # deterministic.
    # =====================================

    original_route_transitions = (
        handoff.route_transitions.copy()
    )

    original_handoffs = (
        handoff.handoffs.copy()
    )

    original_last_camera = (
        handoff.last_camera.copy()
    )

    try:

        # ---------------------------------
        # Clear test state
        # ---------------------------------

        handoff.route_transitions.clear()
        handoff.handoffs.clear()
        handoff.last_camera.clear()

        # =================================
        # TEST GLOBAL ID 2001
        #
        # cam_1 → cam_2 → cam_3
        # =================================

        handoff.update(
            global_id=2001,
            camera_id="cam_1"
        )

        handoff.update(
            global_id=2001,
            camera_id="cam_2"
        )

        handoff.update(
            global_id=2001,
            camera_id="cam_3"
        )

        # =================================
        # TEST GLOBAL ID 2002
        #
        # cam_1 → cam_2
        # =================================

        handoff.update(
            global_id=2002,
            camera_id="cam_1"
        )

        handoff.update(
            global_id=2002,
            camera_id="cam_2"
        )

        # =================================
        # TEST GLOBAL ID 2003
        #
        # cam_1 → cam_3
        # =================================

        handoff.update(
            global_id=2003,
            camera_id="cam_1"
        )

        handoff.update(
            global_id=2003,
            camera_id="cam_3"
        )

        # =====================================
        # PRODUCTION FLOW SERVICE
        # =====================================

        summary = (
            multi_camera_flow.get_summary()
        )

        # =====================================
        # ROUTE LOOKUP
        # =====================================

        route_counts = {}

        for route in summary["routes"]:

            key = (
                route["from_camera"],
                route["to_camera"]
            )

            route_counts[key] = (
                route["transitions"]
            )

        # =====================================
        # VALIDATION
        # =====================================

        validation = {

            "cam1_to_cam2_correct":
                route_counts.get(
                    ("cam_1", "cam_2"),
                    0
                ) == 2,

            "cam2_to_cam3_correct":
                route_counts.get(
                    ("cam_2", "cam_3"),
                    0
                ) == 1,

            "cam1_to_cam3_correct":
                route_counts.get(
                    ("cam_1", "cam_3"),
                    0
                ) == 1,

            "total_routes_correct":
                summary[
                    "total_routes"
                ] == 3,

            "total_transitions_correct":
                summary[
                    "total_transitions"
                ] == 4,

            "cam1_outflow_correct":
                summary[
                    "camera_outflow"
                ].get(
                    "cam_1",
                    0
                ) == 3,

            "cam2_inflow_correct":
                summary[
                    "camera_inflow"
                ].get(
                    "cam_2",
                    0
                ) == 2,

            "cam2_outflow_correct":
                summary[
                    "camera_outflow"
                ].get(
                    "cam_2",
                    0
                ) == 1,

            "cam3_inflow_correct":
                summary[
                    "camera_inflow"
                ].get(
                    "cam_3",
                    0
                ) == 2,

            "cam1_net_flow_correct":
                summary[
                    "camera_net_flow"
                ].get(
                    "cam_1",
                    0
                ) == -3,

            "cam2_net_flow_correct":
                summary[
                    "camera_net_flow"
                ].get(
                    "cam_2",
                    0
                ) == 1,

            "cam3_net_flow_correct":
                summary[
                    "camera_net_flow"
                ].get(
                    "cam_3",
                    0
                ) == 2,

            "production_flow_integration_test_passed":
                (
                    route_counts.get(
                        ("cam_1", "cam_2"),
                        0
                    ) == 2

                    and

                    route_counts.get(
                        ("cam_2", "cam_3"),
                        0
                    ) == 1

                    and

                    route_counts.get(
                        ("cam_1", "cam_3"),
                        0
                    ) == 1

                    and

                    summary[
                        "total_routes"
                    ] == 3

                    and

                    summary[
                        "total_transitions"
                    ] == 4
                )
        }

        return {

            "test":
                "multi_camera_flow_production",

            "summary":
                summary,

            "validation":
                validation
        }

    finally:

        # =====================================
        # RESTORE PRODUCTION STATE
        # =====================================

        handoff.route_transitions[:] = (
            original_route_transitions
        )

        handoff.handoffs[:] = (
            original_handoffs
        )

        handoff.last_camera.clear()

        handoff.last_camera.update(
            original_last_camera
        )


# =====================================
# 4.7G-1 — MULTI-CAMERA FLOW
# NETWORK INTERPRETATION TEST
# =====================================

@router.get("/test/multi-camera-flow-network")
def test_multi_camera_flow_network():

    from app.services.handoff import HandoffTracker
    from app.services.multi_camera_flow import MultiCameraFlow

    # =====================================
    # FRESH TEST INSTANCES
    # =====================================

    test_handoff = HandoffTracker()

    test_flow = MultiCameraFlow(
        test_handoff
    )

    # =====================================
    # BUILD CONTROLLED NETWORK
    #
    # cam_1 → cam_2 = 3
    # cam_1 → cam_3 = 1
    # cam_2 → cam_3 = 2
    #
    # Expected:
    #
    # cam_1 = SOURCE
    # cam_2 = INTERMEDIATE
    # cam_3 = DESTINATION
    # =====================================

    # ---------------------------------
    # cam_1 → cam_2
    # 3 transitions
    # ---------------------------------

    for global_id in [1001, 1002, 1003]:

        test_handoff.update(
            global_id=global_id,
            camera_id="cam_1"
        )

        test_handoff.update(
            global_id=global_id,
            camera_id="cam_2"
        )

    # ---------------------------------
    # cam_1 → cam_3
    # 1 transition
    # ---------------------------------

    test_handoff.update(
        global_id=1004,
        camera_id="cam_1"
    )

    test_handoff.update(
        global_id=1004,
        camera_id="cam_3"
    )

    # ---------------------------------
    # cam_2 → cam_3
    # 2 transitions
    # ---------------------------------

    for global_id in [1005, 1006]:

        test_handoff.update(
            global_id=global_id,
            camera_id="cam_2"
        )

        test_handoff.update(
            global_id=global_id,
            camera_id="cam_3"
        )

    # =====================================
    # GET FLOW DATA
    # =====================================

    route_flow = (
        test_flow.get_route_flow()
    )

    camera_flow = (
        test_flow.get_camera_flow_summary()
    )

    interpretation = (
        test_flow.get_network_interpretation()
    )

    dominant_route = (
        test_flow.get_dominant_route()
    )

    source_cameras = (
        test_flow.get_source_cameras()
    )

    destination_cameras = (
        test_flow.get_destination_cameras()
    )

    intermediate_cameras = (
        test_flow.get_intermediate_cameras()
    )

    balanced_cameras = (
        test_flow.get_balanced_cameras()
    )

    # =====================================
    # ROUTE COUNTS
    # =====================================

    route_counts = {}

    for route in route_flow["routes"]:

        key = (
            route["from_camera"],
            route["to_camera"]
        )

        route_counts[key] = (
            route["transitions"]
        )

    # =====================================
    # VALIDATION
    # =====================================

    validation = {

        # ---------------------------------
        # ROUTE VALIDATION
        # ---------------------------------

        "cam1_to_cam2_correct":
            route_counts.get(
                ("cam_1", "cam_2"),
                0
            ) == 3,

        "cam1_to_cam3_correct":
            route_counts.get(
                ("cam_1", "cam_3"),
                0
            ) == 1,

        "cam2_to_cam3_correct":
            route_counts.get(
                ("cam_2", "cam_3"),
                0
            ) == 2,

        # ---------------------------------
        # NETWORK TOTALS
        # ---------------------------------

        "total_routes_correct":
            route_flow[
                "total_routes"
            ] == 3,

        "total_transitions_correct":
            route_flow[
                "total_transitions"
            ] == 6,

        # ---------------------------------
        # CAMERA FLOW
        # ---------------------------------

        "cam1_source_correct":
            camera_flow[
                "cam_1"
            ]["role"] == "SOURCE",

        "cam2_intermediate_correct":
            camera_flow[
                "cam_2"
            ]["role"] == "INTERMEDIATE",

        "cam3_destination_correct":
            camera_flow[
                "cam_3"
            ]["role"] == "DESTINATION",

        # ---------------------------------
        # SOURCE CAMERA
        # ---------------------------------

        "source_cameras_correct":
            (
                "cam_1"
                in source_cameras
                and
                len(source_cameras) == 1
            ),

        # ---------------------------------
        # DESTINATION CAMERA
        # ---------------------------------

        "destination_cameras_correct":
            (
                "cam_3"
                in destination_cameras
                and
                len(destination_cameras) == 1
            ),

        # ---------------------------------
        # INTERMEDIATE CAMERA
        # ---------------------------------

        "intermediate_cameras_correct":
            (
                "cam_2"
                in intermediate_cameras
                and
                len(intermediate_cameras) == 1
            ),

        # ---------------------------------
        # NO BALANCED CAMERA
        # ---------------------------------

        "balanced_cameras_correct":
            len(
                balanced_cameras
            ) == 0,

        # ---------------------------------
        # DOMINANT ROUTE
        # ---------------------------------

        "dominant_route_correct":
            (
                dominant_route is not None
                and
                dominant_route[
                    "from_camera"
                ] == "cam_1"
                and
                dominant_route[
                    "to_camera"
                ] == "cam_2"
                and
                dominant_route[
                    "transitions"
                ] == 3
            ),

        # ---------------------------------
        # NETWORK STATUS
        # ---------------------------------

        "network_status_correct":
            interpretation[
                "network_status"
            ] == "ACTIVE_NETWORK",

        # ---------------------------------
        # BUSIEST SOURCE
        # ---------------------------------

        "busiest_source_correct":
            interpretation[
                "busiest_source"
            ] == "cam_1",

        # ---------------------------------
        # BUSIEST DESTINATION
        # ---------------------------------

        "busiest_destination_correct":
            interpretation[
                "busiest_destination"
            ] == "cam_3",

        # ---------------------------------
        # OVERALL TEST
        # ---------------------------------

        "multi_camera_flow_network_test_passed":
            (
                route_counts.get(
                    ("cam_1", "cam_2"),
                    0
                ) == 3

                and

                route_counts.get(
                    ("cam_1", "cam_3"),
                    0
                ) == 1

                and

                route_counts.get(
                    ("cam_2", "cam_3"),
                    0
                ) == 2

                and

                route_flow[
                    "total_routes"
                ] == 3

                and

                route_flow[
                    "total_transitions"
                ] == 6

                and

                camera_flow[
                    "cam_1"
                ]["role"] == "SOURCE"

                and

                camera_flow[
                    "cam_2"
                ]["role"] == "INTERMEDIATE"

                and

                camera_flow[
                    "cam_3"
                ]["role"] == "DESTINATION"

                and

                dominant_route is not None

                and

                dominant_route[
                    "from_camera"
                ] == "cam_1"

                and

                dominant_route[
                    "to_camera"
                ] == "cam_2"

                and

                dominant_route[
                    "transitions"
                ] == 3

                and

                interpretation[
                    "network_status"
                ] == "ACTIVE_NETWORK"

                and

                interpretation[
                    "busiest_source"
                ] == "cam_1"

                and

                interpretation[
                    "busiest_destination"
                ] == "cam_3"
            )
    }

    # =====================================
    # RESPONSE
    # =====================================

    return {

        "test":
            "multi_camera_flow_network",

        "route_flow":
            route_flow,

        "camera_flow":
            camera_flow,

        "interpretation":
            interpretation,

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

        "validation":
            validation
    }

@router.get("/test/handoff-transition-integrity")
def test_handoff_transition_integrity():

    from app.services.handoff import HandoffTracker

    tracker = HandoffTracker()

    # =====================================
    # TEST 1 — FIRST OBSERVATION
    # =====================================

    first = tracker.update(
        global_id=1001,
        camera_id="cam_1"
    )

    test_1 = (
        first is None
        and
        tracker.last_camera.get(1001) == "cam_1"
        and
        len(tracker.route_transitions) == 0
        and
        len(tracker.handoffs) == 0
    )

    # =====================================
    # TEST 2 — SAME CAMERA
    # =====================================

    same_camera = tracker.update(
        global_id=1001,
        camera_id="cam_1"
    )

    test_2 = (
        same_camera is None
        and
        len(tracker.route_transitions) == 0
        and
        len(tracker.handoffs) == 0
    )

    # =====================================
    # TEST 3 — CAM_1 → CAM_2
    # =====================================

    transition_1 = tracker.update(
        global_id=1001,
        camera_id="cam_2"
    )

    test_3 = (
        transition_1 is not None
        and
        transition_1["from_camera"] == "cam_1"
        and
        transition_1["to_camera"] == "cam_2"
        and
        len(tracker.route_transitions) == 1
        and
        len(tracker.handoffs) == 1
        and
        tracker.last_camera.get(1001) == "cam_2"
    )

    # =====================================
    # TEST 4 — REPEATED CAM_2
    # =====================================

    repeated = tracker.update(
        global_id=1001,
        camera_id="cam_2"
    )

    test_4 = (
        repeated is None
        and
        len(tracker.route_transitions) == 1
        and
        len(tracker.handoffs) == 1
    )

    # =====================================
    # TEST 5 — CAM_2 → CAM_3
    # =====================================

    transition_2 = tracker.update(
        global_id=1001,
        camera_id="cam_3"
    )

    test_5 = (
        transition_2 is not None
        and
        transition_2["from_camera"] == "cam_2"
        and
        transition_2["to_camera"] == "cam_3"
        and
        len(tracker.route_transitions) == 2
        and
        len(tracker.handoffs) == 2
        and
        tracker.last_camera.get(1001) == "cam_3"
    )

    # =====================================
    # TEST 6 — INVALID GLOBAL ID
    # =====================================

    invalid_global = tracker.update(
        global_id=None,
        camera_id="cam_1"
    )

    test_6 = (
        invalid_global is None
        and
        tracker.invalid_observations == 1
        and
        len(tracker.route_transitions) == 2
    )

    # =====================================
    # TEST 7 — INVALID CAMERA
    # =====================================

    invalid_camera = tracker.update(
        global_id=1002,
        camera_id=""
    )

    test_7 = (
        invalid_camera is None
        and
        tracker.invalid_observations == 2
        and
        len(tracker.route_transitions) == 2
    )

    # =====================================
    # TEST 8 — TIMESTAMP CONSISTENCY
    # =====================================

    timestamp_consistent = (
        tracker.route_transitions[0]["timestamp"]
        ==
        tracker.handoffs[0]["timestamp"]
    )

    test_8 = timestamp_consistent

    # =====================================
    # OVERALL RESULT
    # =====================================

    all_passed = all([
        test_1,
        test_2,
        test_3,
        test_4,
        test_5,
        test_6,
        test_7,
        test_8
    ])

    return {

        "test":
            "handoff_transition_integrity",

        "tests": {

            "first_observation":
                test_1,

            "same_camera_no_duplicate":
                test_2,

            "cam1_to_cam2_transition":
                test_3,

            "repeated_camera_no_duplicate":
                test_4,

            "cam2_to_cam3_transition":
                test_5,

            "invalid_global_id_rejected":
                test_6,

            "invalid_camera_rejected":
                test_7,

            "timestamp_consistency":
                test_8
        },

        "state": {

            "last_camera":
                tracker.last_camera,

            "route_transitions":
                tracker.route_transitions,

            "handoffs":
                tracker.handoffs,

            "invalid_observations":
                tracker.invalid_observations
        },

        "passed":
            all_passed
    }



@router.get("/test/camera-route-confidence")
def test_camera_route_confidence():

    from app.services.handoff import HandoffTracker

    test_handoff = HandoffTracker()

    # =====================================
    # CONTROLLED ROUTE HISTORY
    #
    # cam_1 → cam_2 = 3
    # cam_1 → cam_3 = 1
    #
    # Therefore:
    #
    # cam_1 → cam_2 = 0.75
    # cam_1 → cam_3 = 0.25
    # =====================================

    for global_id in [1001, 1002, 1003]:

        test_handoff.update(
            global_id=global_id,
            camera_id="cam_1"
        )

        test_handoff.update(
            global_id=global_id,
            camera_id="cam_2"
        )

    test_handoff.update(
        global_id=1004,
        camera_id="cam_1"
    )

    test_handoff.update(
        global_id=1004,
        camera_id="cam_3"
    )

    # =====================================
    # LEARN ROUTE CONFIDENCE
    # =====================================

    confidence = (
        test_handoff.get_route_confidence()
    )

    routes = confidence["routes"]

    # =====================================
    # FIND ROUTES
    # =====================================

    route_lookup = {

        (
            route["from_camera"],
            route["to_camera"]
        ):
            route

        for route in routes
    }

    cam1_cam2 = route_lookup.get(
        ("cam_1", "cam_2")
    )

    cam1_cam3 = route_lookup.get(
        ("cam_1", "cam_3")
    )

    # =====================================
    # VALIDATION
    # =====================================

    validation = {

        "cam1_to_cam2_exists":
            cam1_cam2 is not None,

        "cam1_to_cam3_exists":
            cam1_cam3 is not None,

        "cam1_to_cam2_confidence_correct":
            (
                cam1_cam2 is not None
                and
                cam1_cam2["confidence"] == 0.75
            ),

        "cam1_to_cam3_confidence_correct":
            (
                cam1_cam3 is not None
                and
                cam1_cam3["confidence"] == 0.25
            ),

        "confidence_sum_correct":
            (
                cam1_cam2 is not None
                and
                cam1_cam3 is not None
                and
                round(
                    cam1_cam2["confidence"]
                    +
                    cam1_cam3["confidence"],
                    4
                ) == 1.0
            ),

        "confidence_bounds_correct":
            all(
                0.0 <= route["confidence"] <= 1.0
                for route in routes
            ),

        "transition_counts_correct":
            (
                cam1_cam2 is not None
                and
                cam1_cam3 is not None
                and
                cam1_cam2["transitions"] == 3
                and
                cam1_cam3["transitions"] == 1
            )
    }

    validation[
        "camera_route_confidence_test_passed"
    ] = all(
        validation.values()
    )

    return {

        "test":
            "camera_route_confidence",

        "confidence":
            confidence,

        "validation":
            validation
    }


# =====================================
# 4.7B-2-2 — MOST LIKELY NEXT CAMERA TEST
# =====================================

@router.get("/test/most-likely-next-camera")
def test_most_likely_next_camera():

    from app.services.handoff import HandoffTracker

    # =====================================
    # FRESH TEST INSTANCE
    # =====================================

    test_handoff = HandoffTracker()

    # =====================================
    # BUILD ROUTE HISTORY
    #
    # cam_1 → cam_2 = 3
    # cam_1 → cam_3 = 1
    # =====================================

    for global_id in [1001, 1002, 1003]:

        test_handoff.update(
            global_id=global_id,
            camera_id="cam_1"
        )

        test_handoff.update(
            global_id=global_id,
            camera_id="cam_2"
        )

    test_handoff.update(
        global_id=1004,
        camera_id="cam_1"
    )

    test_handoff.update(
        global_id=1004,
        camera_id="cam_3"
    )

    # =====================================
    # TEST PREDICTION
    # =====================================

    prediction = (
        test_handoff.get_most_likely_next_camera(
            "cam_1"
        )
    )

    # =====================================
    # VALIDATION
    # =====================================

    validation = {

        "predicted_camera_correct":
            prediction[
                "predicted_camera"
            ] == "cam_2",

        "confidence_correct":
            prediction[
                "confidence"
            ] == 0.75,

        "transitions_correct":
            prediction[
                "transitions"
            ] == 3,

        "known_routes_correct":
            prediction[
                "known_routes"
            ] == 2,

        "most_likely_next_camera_test_passed":
            (
                prediction[
                    "predicted_camera"
                ] == "cam_2"

                and

                prediction[
                    "confidence"
                ] == 0.75

                and

                prediction[
                    "transitions"
                ] == 3

                and

                prediction[
                    "known_routes"
                ] == 2
            )
    }

    return {

        "test":
            "most_likely_next_camera",

        "prediction":
            prediction,

        "validation":
            validation
    }


# =====================================
# 4.7B-2-3 — GLOBAL-ID ROUTE PREDICTION TEST
# =====================================

@router.get("/test/global-id-route-prediction")
def test_global_id_route_prediction():

    from app.services.handoff import HandoffTracker

    # =====================================
    # FRESH TEST INSTANCE
    # =====================================

    test_handoff = HandoffTracker()

    # =====================================
    # BUILD ROUTE HISTORY
    #
    # cam_1 → cam_2 = 3
    # cam_1 → cam_3 = 1
    # =====================================

    for global_id in [1001, 1002, 1003]:

        test_handoff.update(
            global_id=global_id,
            camera_id="cam_1"
        )

        test_handoff.update(
            global_id=global_id,
            camera_id="cam_2"
        )

    test_handoff.update(
        global_id=1004,
        camera_id="cam_1"
    )

    test_handoff.update(
        global_id=1004,
        camera_id="cam_3"
    )

    # =====================================
    # TEST GLOBAL-ID PREDICTION
    #
    # Global ID 1005 is currently at cam_1
    # =====================================

    test_handoff.update(
        global_id=1005,
        camera_id="cam_1"
    )

    prediction = (
        test_handoff.get_global_id_route_prediction(
            1005
        )
    )

    # =====================================
    # VALIDATION
    # =====================================

    validation = {

        "global_id_correct":
            prediction[
                "global_id"
            ] == 1005,

        "current_camera_correct":
            prediction[
                "current_camera"
            ] == "cam_1",

        "predicted_camera_correct":
            prediction[
                "predicted_camera"
            ] == "cam_2",

        "confidence_correct":
            prediction[
                "confidence"
            ] == 0.75,

        "transitions_correct":
            prediction[
                "transitions"
            ] == 3,

        "known_routes_correct":
            prediction[
                "known_routes"
            ] == 2,

        "global_id_route_prediction_test_passed":
            (
                prediction[
                    "global_id"
                ] == 1005

                and

                prediction[
                    "current_camera"
                ] == "cam_1"

                and

                prediction[
                    "predicted_camera"
                ] == "cam_2"

                and

                prediction[
                    "confidence"
                ] == 0.75

                and

                prediction[
                    "transitions"
                ] == 3

                and

                prediction[
                    "known_routes"
                ] == 2
            )
    }

    return {

        "test":
            "global_id_route_prediction",

        "prediction":
            prediction,

        "validation":
            validation
    }


@router.get("/multi-camera-forecast")
def get_multi_camera_forecast(
    lookback_seconds: int = 300
):
    return fusion.get_multi_camera_forecast(
        lookback_seconds=lookback_seconds
    )


@router.get("/test/multi-camera-forecast")
def test_multi_camera_forecast():
    # -------------------------------------------------
    # Fresh isolated test components
    # -------------------------------------------------

    test_handoff = HandoffTracker()
    test_registry = GlobalTrackRegistry()

    forecast = MultiCameraForecast(
        handoff=test_handoff,
        global_registry=test_registry
    )

    now = time.time()

    # -------------------------------------------------
    # Seed current global occupancy
    # -------------------------------------------------

    test_registry.register_track(
        camera_id="camera_1",
        local_track_id=1
    )

    test_registry.register_track(
        camera_id="camera_1",
        local_track_id=2
    )

    test_registry.register_track(
        camera_id="camera_2",
        local_track_id=3
    )

    # -------------------------------------------------
    # Controlled transition history
    #
    # camera_1 → camera_2 : 6
    # camera_1 → camera_3 : 3
    # camera_2 → camera_3 : 4
    # -------------------------------------------------

    transitions = []

    for i in range(6):
        transitions.append({
            "global_id": 1000 + i,
            "from_camera": "camera_1",
            "to_camera": "camera_2",
            "timestamp": now - 60 + i
        })

    for i in range(3):
        transitions.append({
            "global_id": 1100 + i,
            "from_camera": "camera_1",
            "to_camera": "camera_3",
            "timestamp": now - 45 + i
        })

    for i in range(4):
        transitions.append({
            "global_id": 1200 + i,
            "from_camera": "camera_2",
            "to_camera": "camera_3",
            "timestamp": now - 30 + i
        })

    test_handoff.route_transitions = transitions

    # -------------------------------------------------
    # Generate forecast
    # -------------------------------------------------

    result = forecast.get_summary(
        lookback_seconds=300
    )

    # -------------------------------------------------
    # Validation
    # -------------------------------------------------

    validation = {
        "forecast_horizons_present": (
            "forecast_horizons" in result
            and all(
                horizon in result["forecast_horizons"]
                for horizon in ["30s", "60s", "300s"]
            )
        ),

        "camera_forecast_present": all(
            "camera_forecast" in result["forecast_horizons"][horizon]
            for horizon in ["30s", "60s", "300s"]
        ),

        "route_forecast_present": all(
            "route_forecast" in result["forecast_horizons"][horizon]
            for horizon in ["30s", "60s", "300s"]
        ),

        "dominant_route_present": (
            result.get("dominant_predicted_route") is not None
        ),

        "network_status_present": (
            result.get("network_status") is not None
        ),

        "flow_scope_correct": (
            result.get("flow_scope")
            == "INTERNAL_CAMERA_TRANSITIONS"
        ),

        "observed_transition_count_valid": (
            result.get("observed_transition_count")
            == len(transitions)
        ),

        "transitions_observed": len(transitions)
    }

    validation["passed"] = all([
        validation["forecast_horizons_present"],
        validation["camera_forecast_present"],
        validation["route_forecast_present"],
        validation["dominant_route_present"],
        validation["network_status_present"],
        validation["flow_scope_correct"],
        validation["observed_transition_count_valid"]
    ])

    return {
        "test": "multi_camera_forecast",
        "status": (
            "PASS"
            if validation["passed"]
            else "FAIL"
        ),
        "validation": validation,
        "forecast": result
    }
