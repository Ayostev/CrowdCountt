# app/services/congestion_forecast.py

from collections import defaultdict, deque


class CongestionForecast:

    """
    Predict future congestion
    using recent zone occupancy history.
    """

    HISTORY_SIZE = 120

    def __init__(self):

        # zone -> occupancy history
        self.zone_history = defaultdict(
            lambda: deque(maxlen=self.HISTORY_SIZE)
        )

    # =====================================
    # UPDATE
    # =====================================
    def update(self, zone_counts):

        for zone, count in zone_counts.items():

            self.zone_history[zone].append(count)

    # =====================================
    # SIMPLE TREND FORECAST
    # =====================================
    def predict_zone(self, zone):

        history = self.zone_history.get(zone)

        if not history or len(history) < 2:

            return {
                "current": 0,
                "predicted": 0,
                "risk": "LOW"
            }

        current = history[-1]

        trend = history[-1] - history[0]

        predicted = max(
            0,
            round(current + trend)
        )

        if predicted >= current * 1.5 and predicted > 10:

            risk = "HIGH"

        elif predicted > current:

            risk = "MEDIUM"

        else:

            risk = "LOW"

        return {

            "current": current,

            "predicted": predicted,

            "risk": risk
        }

    # =====================================
    # SUMMARY
    # =====================================
    def get_summary(self):

        result = {}

        for zone in self.zone_history:

            result[zone] = self.predict_zone(zone)

        return {
            "zones": result
        }


congestion_forecast = CongestionForecast()