# app/routes/multi_camera_flow_test.py

from fastapi import APIRouter

from app.services.handoff import HandoffTracker
from app.services.multi_camera_flow import MultiCameraFlow


router = APIRouter(
    prefix="/api/test",
    tags=["Multi-Camera Flow Test"]
)


@router.get("/multi-camera-flow")
def test_multi_camera_flow():

    # =====================================
    # FRESH TEST INSTANCES
    # =====================================

    test_handoff = HandoffTracker()

    test_flow = MultiCameraFlow(
        test_handoff
    )

    # =====================================
    # PERSON 1001
    #
    # cam_1 → cam_2
    # cam_2 → cam_3
    # =====================================

    test_handoff.update(
        global_id=1001,
        camera_id="cam_1"
    )

    test_handoff.update(
        global_id=1001,
        camera_id="cam_2"
    )

    test_handoff.update(
        global_id=1001,
        camera_id="cam_3"
    )

    # =====================================
    # PERSON 1002
    #
    # cam_1 → cam_2
    # =====================================

    test_handoff.update(
        global_id=1002,
        camera_id="cam_1"
    )

    test_handoff.update(
        global_id=1002,
        camera_id="cam_2"
    )

    # =====================================
    # PERSON 1003
    #
    # cam_1 → cam_3
    # =====================================

    test_handoff.update(
        global_id=1003,
        camera_id="cam_1"
    )

    test_handoff.update(
        global_id=1003,
        camera_id="cam_3"
    )

    # =====================================
    # GET FLOW SUMMARY
    # =====================================

    summary = (
        test_flow.get_summary()
    )

    # =====================================
    # GET COMPONENTS
    # =====================================

    inflow = (
        test_flow.get_camera_inflow()
    )

    outflow = (
        test_flow.get_camera_outflow()
    )

    net_flow = (
        test_flow.get_camera_net_flow()
    )

    route_flow = (
        test_flow.get_route_flow()
    )

    # =====================================
    # VALIDATION
    # =====================================

    route_counts = {}

    for route in route_flow[
        "routes"
    ]:

        key = (
            route["from_camera"],
            route["to_camera"]
        )

        route_counts[key] = (
            route["transitions"]
        )

    validation = {

        # ---------------------------------
        # ROUTE COUNTS
        # ---------------------------------

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

        # ---------------------------------
        # TOTAL ROUTES
        # ---------------------------------

        "total_routes_correct":
            route_flow[
                "total_routes"
            ] == 3,

        # ---------------------------------
        # TOTAL TRANSITIONS
        # ---------------------------------

        "total_transitions_correct":
            route_flow[
                "total_transitions"
            ] == 4,

        # ---------------------------------
        # INFLOW
        #
        # cam_2 receives:
        #   1001
        #   1002
        #
        # cam_3 receives:
        #   1001
        #   1003
        # ---------------------------------

        "cam2_inflow_correct":
            inflow.get(
                "cam_2",
                0
            ) == 2,

        "cam3_inflow_correct":
            inflow.get(
                "cam_3",
                0
            ) == 2,

        # ---------------------------------
        # OUTFLOW
        #
        # cam_1 sends:
        #   1001
        #   1002
        #   1003
        #
        # cam_2 sends:
        #   1001
        # ---------------------------------

        "cam1_outflow_correct":
            outflow.get(
                "cam_1",
                0
            ) == 3,

        "cam2_outflow_correct":
            outflow.get(
                "cam_2",
                0
            ) == 1,

        # ---------------------------------
        # NET FLOW
        # ---------------------------------

        "cam1_net_flow_correct":
            net_flow.get(
                "cam_1",
                0
            ) == -3,

        "cam2_net_flow_correct":
            net_flow.get(
                "cam_2",
                0
            ) == 1,

        "cam3_net_flow_correct":
            net_flow.get(
                "cam_3",
                0
            ) == 2,

        # ---------------------------------
        # OVERALL
        # ---------------------------------

        "multi_camera_flow_test_passed":
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

                route_flow[
                    "total_routes"
                ] == 3

                and

                route_flow[
                    "total_transitions"
                ] == 4

                and

                inflow.get(
                    "cam_2",
                    0
                ) == 2

                and

                inflow.get(
                    "cam_3",
                    0
                ) == 2

                and

                outflow.get(
                    "cam_1",
                    0
                ) == 3

                and

                outflow.get(
                    "cam_2",
                    0
                ) == 1

                and

                net_flow.get(
                    "cam_1",
                    0
                ) == -3

                and

                net_flow.get(
                    "cam_2",
                    0
                ) == 1

                and

                net_flow.get(
                    "cam_3",
                    0
                ) == 2
            )
    }

    return {

        "test":
            "multi_camera_flow",

        "route_flow":
            route_flow,

        "camera_inflow":
            inflow,

        "camera_outflow":
            outflow,

        "camera_net_flow":
            net_flow,

        "summary":
            summary,

        "validation":
            validation
    }



# =====================================
# 4.7G-2 — MULTI-CAMERA FLOW
# PRODUCTION INTEGRATION TEST
# =====================================

@router.get("/test/multi-camera-flow-production")
def test_multi_camera_flow_production():

    from app.services.handoff import handoff
    from app.services.multi_camera_flow import (
        multi_camera_flow
    )

    # =====================================
    # IMPORTANT
    # =====================================
    #
    # This test intentionally uses the
    # PRODUCTION SINGLETONS:
    #
    #     handoff
    #     multi_camera_flow
    #
    # It does NOT create a new
    # HandoffTracker instance.
    #
    # Therefore this test verifies that
    # the production MultiCameraFlow service
    # consumes the authoritative production
    # HandoffTracker.route_transitions state.
    #
    # =====================================

    # =====================================
    # CAPTURE INITIAL STATE
    # =====================================

    initial_transitions = len(
        handoff.route_transitions
    )

    # =====================================
    # CREATE CONTROLLED PRODUCTION
    # TRANSITIONS
    #
    # These are added directly to the
    # production handoff singleton so that
    # MultiCameraFlow must consume them.
    #
    # =====================================

    test_global_ids = [
        9101,
        9102,
        9103,
        9104,
        9105
    ]

    # ---------------------------------
    # cam_1 → cam_2
    # 3 transitions
    # ---------------------------------

    for global_id in [
        9101,
        9102,
        9103
    ]:

        handoff.update(
            global_id=global_id,
            camera_id="cam_1"
        )

        handoff.update(
            global_id=global_id,
            camera_id="cam_2"
        )

    # ---------------------------------
    # cam_1 → cam_3
    # 1 transition
    # ---------------------------------

    handoff.update(
        global_id=9104,
        camera_id="cam_1"
    )

    handoff.update(
        global_id=9104,
        camera_id="cam_3"
    )

    # ---------------------------------
    # cam_2 → cam_3
    # 1 transition
    # ---------------------------------

    handoff.update(
        global_id=9105,
        camera_id="cam_2"
    )

    handoff.update(
        global_id=9105,
        camera_id="cam_3"
    )

    # =====================================
    # READ PRODUCTION FLOW SERVICE
    # =====================================

    summary = (
        multi_camera_flow.get_summary()
    )

    # =====================================
    # BUILD ROUTE LOOKUP
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
    # EXPECTED NEW TRANSITIONS
    # =====================================

    expected_new_transitions = 5

    expected_total_transitions = (
        initial_transitions
        +
        expected_new_transitions
    )

    # =====================================
    # VALIDATION
    # =====================================

    validation = {

        # ---------------------------------
        # PRODUCTION STATE WAS UPDATED
        # ---------------------------------

        "production_handoff_updated":
            (
                len(
                    handoff.route_transitions
                )
                ==
                expected_total_transitions
            ),

        # ---------------------------------
        # ROUTE 1
        # ---------------------------------

        "cam1_to_cam2_correct":
            (
                route_counts.get(
                    ("cam_1", "cam_2"),
                    0
                )
                >= 3
            ),

        # ---------------------------------
        # ROUTE 2
        # ---------------------------------

        "cam1_to_cam3_correct":
            (
                route_counts.get(
                    ("cam_1", "cam_3"),
                    0
                )
                >= 1
            ),

        # ---------------------------------
        # ROUTE 3
        # ---------------------------------

        "cam2_to_cam3_correct":
            (
                route_counts.get(
                    ("cam_2", "cam_3"),
                    0
                )
                >= 1
            ),

        # ---------------------------------
        # MULTI-CAMERA SERVICE CONSUMED
        # PRODUCTION HANDOFF STATE
        # ---------------------------------

        "production_flow_consumed":
            (
                summary[
                    "total_transitions"
                ]
                ==
                expected_total_transitions
            ),

        # ---------------------------------
        # ROUTE COUNT
        # ---------------------------------

        "route_count_correct":
            (
                summary[
                    "total_routes"
                ]
                >= 3
            ),

        # ---------------------------------
        # CAMERA INFLOW
        # ---------------------------------

        "cam2_inflow_present":
            (
                summary[
                    "camera_inflow"
                ].get(
                    "cam_2",
                    0
                )
                >= 3
            ),

        "cam3_inflow_present":
            (
                summary[
                    "camera_inflow"
                ].get(
                    "cam_3",
                    0
                )
                >= 2
            ),

        # ---------------------------------
        # CAMERA OUTFLOW
        # ---------------------------------

        "cam1_outflow_present":
            (
                summary[
                    "camera_outflow"
                ].get(
                    "cam_1",
                    0
                )
                >= 4
            ),

        "cam2_outflow_present":
            (
                summary[
                    "camera_outflow"
                ].get(
                    "cam_2",
                    0
                )
                >= 1
            ),

        # ---------------------------------
        # NET FLOW
        # ---------------------------------

        "cam1_net_flow_present":
            (
                summary[
                    "camera_net_flow"
                ].get(
                    "cam_1",
                    0
                )
                <= -4
            ),

        "cam2_net_flow_present":
            (
                summary[
                    "camera_net_flow"
                ].get(
                    "cam_2",
                    0
                )
                >= 2
            ),

        "cam3_net_flow_present":
            (
                summary[
                    "camera_net_flow"
                ].get(
                    "cam_3",
                    0
                )
                >= 2
            ),

        # ---------------------------------
        # OVERALL PRODUCTION INTEGRATION
        # ---------------------------------

        "production_flow_integration_test_passed":
            (
                len(
                    handoff.route_transitions
                )
                ==
                expected_total_transitions

                and

                summary[
                    "total_transitions"
                ]
                ==
                expected_total_transitions

                and

                route_counts.get(
                    ("cam_1", "cam_2"),
                    0
                )
                >= 3

                and

                route_counts.get(
                    ("cam_1", "cam_3"),
                    0
                )
                >= 1

                and

                route_counts.get(
                    ("cam_2", "cam_3"),
                    0
                )
                >= 1

                and

                summary[
                    "total_routes"
                ]
                >= 3
            )
    }

    # =====================================
    # RESPONSE
    # =====================================

    return {

        "test":
            "multi_camera_flow_production",

        "initial_transitions":
            initial_transitions,

        "expected_new_transitions":
            expected_new_transitions,

        "final_transitions":
            len(
                handoff.route_transitions
            ),

        "summary":
            summary,

        "validation":
            validation
    }

