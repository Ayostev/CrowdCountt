# app/services/queue_prediction.py

from collections import defaultdict, deque


class QueuePrediction:

    """
    Predict future queue formation.

    Uses:
    - occupancy history
    - congestion trends

    Forecasts whether a zone
    is likely to become a queue.
    """

    HISTORY_SIZE = 120

    def __init__(self):

        self.zone_history = defaultdict(
            lambda: deque(maxlen=self.HISTORY_SIZE)
        )

    # =====================================
    # UPDATE
    # =====================================
    def update(self, occupancy):

        for zone, count in occupancy.items():

            self.zone_history[zone].append(
                count
            )

    # =====================================
    # PREDICT ZONE
    # =====================================
    def predict_zone(self, zone):

        history = self.zone_history.get(zone)

        if not history or len(history) < 2:

            return {
                "current": 0,
                "predicted": 0,
                "risk": "LOW",
                "predicted_queue": False
            }

        current = history[-1]

        trend = history[-1] - history[0]

        predicted = max(
            0,
            round(current + trend)
        )

        # ---------------------------------
        # Queue Forecast
        # ---------------------------------

        predicted_queue = predicted >= 3

        if predicted >= 6:

            risk = "HIGH"

        elif predicted >= 3:

            risk = "MEDIUM"

        else:

            risk = "LOW"

        return {

            "current": current,

            "predicted": predicted,

            "risk": risk,

            "predicted_queue": predicted_queue
        }

    # =====================================
    # SUMMARY
    # =====================================
    def get_summary(self):

        result = {}

        for zone in self.zone_history:

            result[zone] = self.predict_zone(
                zone
            )

        return {
            "queue_predictions": result
        }


queue_prediction = QueuePrediction()