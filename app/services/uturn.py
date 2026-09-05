# app/services/uturn.py

class UTurnAnalytics:
    """
    Behavioral Analytics

    U-Turn Detection
    ----------------
    Detects reversal of movement direction.
    """

    UTURN_PAIRS = {

        "NORTH": "SOUTH",
        "SOUTH": "NORTH",

        "EAST": "WEST",
        "WEST": "EAST",

        "NORTH-EAST": "SOUTH-WEST",
        "SOUTH-WEST": "NORTH-EAST",

        "NORTH-WEST": "SOUTH-EAST",
        "SOUTH-EAST": "NORTH-WEST"
    }

    def __init__(self):

        self.uturn_tracks = set()

        self.uturn_events = []

    # =====================================
    # UPDATE
    # =====================================
    def update(
        self,
        track_id,
        dominant_direction,
        current_direction
    ):

        expected = self.UTURN_PAIRS.get(
            dominant_direction
        )

        if expected is None:
            return

        if current_direction == expected:

            if track_id not in self.uturn_tracks:

                self.uturn_tracks.add(track_id)

                self.uturn_events.append({

                    "track_id": track_id,

                    "from": dominant_direction,

                    "to": current_direction
                })

        else:

            self.uturn_tracks.discard(track_id)

    # =====================================
    # TRACK STATUS
    # =====================================
    def is_uturn(self, track_id):

        return track_id in self.uturn_tracks

    # =====================================
    # SUMMARY
    # =====================================
    def get_summary(self):

        return {

            "active_uturns": len(
                self.uturn_tracks
            ),

            "track_ids": sorted(
                self.uturn_tracks
            ),

            "recent_events": self.uturn_events[-20:]
        }


uturn = UTurnAnalytics()