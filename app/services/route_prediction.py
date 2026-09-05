# app/services/route_prediction.py

from collections import defaultdict


class RoutePrediction:

    """
    Predict future movement direction
    using trajectory consistency.
    """

    def __init__(self):

        self.predictions = {}

    # =====================================
    # UPDATE
    # =====================================
    def update(
        self,
        track_id,
        current_direction,
        dominant_direction
    ):

        confidence = 0.5

        if (
            current_direction == dominant_direction
            and current_direction != "STATIONARY"
        ):
            confidence = 0.9

        elif dominant_direction != "STATIONARY":
            confidence = 0.7

        self.predictions[track_id] = {

            "track_id": track_id,

            "current_direction": current_direction,

            "predicted_direction": dominant_direction,

            "confidence": round(
                confidence,
                2
            )
        }

    # =====================================
    # TRACK PREDICTION
    # =====================================
    def get_track_prediction(
        self,
        track_id
    ):

        return self.predictions.get(
            track_id,
            {}
        )

    # =====================================
    # ALL PREDICTIONS
    # =====================================
    def get_summary(self):

        return {

            "active_predictions": len(
                self.predictions
            ),

            "predictions": list(
                self.predictions.values()
            )
        }


route_prediction = RoutePrediction()