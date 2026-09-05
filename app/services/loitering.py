# app/services/loitering.py

class LoiteringAnalytics:
    """
    Behavioral Analytics

    Loitering Detection
    -------------------
    Long duration
    + Low speed
    + Limited movement
    """

    MIN_DURATION = 30      # seconds
    MAX_SPEED = 25         # px/sec
    MAX_DISTANCE = 300     # pixels

    def __init__(self):

        self.loitering_tracks = set()

    # =====================================
    # UPDATE
    # =====================================
    def update(
        self,
        track_id,
        duration,
        speed,
        distance
    ):

        is_loitering = (

            duration >= self.MIN_DURATION

            and

            speed <= self.MAX_SPEED

            and

            distance <= self.MAX_DISTANCE
        )

        if is_loitering:

            self.loitering_tracks.add(track_id)

        else:

            self.loitering_tracks.discard(track_id)

    # =====================================
    # TRACK STATUS
    # =====================================
    def is_loitering(self, track_id):

        return track_id in self.loitering_tracks

    # =====================================
    # SUMMARY
    # =====================================
    def get_summary(self):

        return {

            "active_loiterers": len(
                self.loitering_tracks
            ),

            "track_ids": sorted(
                self.loitering_tracks
            )
        }


loitering = LoiteringAnalytics()