# app/services/prediction.py

class OccupancyPrediction:

    """
    Occupancy Forecasting

    Predict:
    - 30 second occupancy
    - 60 second occupancy

    Based on recent trend.
    """

    HISTORY_WINDOW = 30

    def get_prediction(self, history):

        if len(history) < 2:

            return {
                "current": 0,
                "predicted_30s": 0,
                "predicted_60s": 0,
                "trend": "STABLE"
            }

        recent = history[-self.HISTORY_WINDOW:]

        occupancies = [
            item["occupancy"]
            for item in recent
        ]

        current = occupancies[-1]

        oldest = occupancies[0]

        trend_per_sample = (
            current - oldest
        ) / max(len(occupancies) - 1, 1)

        predicted_30 = max(
            0,
            round(
                current +
                trend_per_sample * 30
            )
        )

        predicted_60 = max(
            0,
            round(
                current +
                trend_per_sample * 60
            )
        )

        if trend_per_sample > 0.1:

            trend = "RISING"

        elif trend_per_sample < -0.1:

            trend = "FALLING"

        else:

            trend = "STABLE"

        return {

            "current": current,

            "predicted_30s": predicted_30,

            "predicted_60s": predicted_60,

            "trend": trend
        }


prediction = OccupancyPrediction()