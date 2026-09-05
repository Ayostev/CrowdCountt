# app/services/flow_forecast.py

from collections import deque


class FlowForecast:
    """
    Predict future crowd flow.

    Uses:
    - entry rate
    - exit rate
    - net flow trend
    """

    HISTORY_SIZE = 120

    def __init__(self):

        self.entry_history = deque(
            maxlen=self.HISTORY_SIZE
        )

        self.exit_history = deque(
            maxlen=self.HISTORY_SIZE
        )

    # =====================================
    # UPDATE
    # =====================================
    def update(
        self,
        entry_rate,
        exit_rate
    ):

        self.entry_history.append(
            entry_rate
        )

        self.exit_history.append(
            exit_rate
        )

    # =====================================
    # FORECAST
    # =====================================
    def get_summary(self):

        if len(self.entry_history) < 2:

            return {

                "current_entry_rate": 0,
                "current_exit_rate": 0,

                "predicted_entry_rate": 0,
                "predicted_exit_rate": 0,

                "predicted_net_flow": 0,

                "trend": "STABLE"
            }

        current_entry = self.entry_history[-1]
        current_exit = self.exit_history[-1]

        entry_trend = (
            self.entry_history[-1]
            - self.entry_history[0]
        )

        exit_trend = (
            self.exit_history[-1]
            - self.exit_history[0]
        )

        predicted_entry = max(
            0,
            round(current_entry + entry_trend, 2)
        )

        predicted_exit = max(
            0,
            round(current_exit + exit_trend, 2)
        )

        predicted_net_flow = round(
            predicted_entry - predicted_exit,
            2
        )

        if predicted_net_flow > 5:

            trend = "INCREASING"

        elif predicted_net_flow < -5:

            trend = "DECREASING"

        else:

            trend = "STABLE"

        return {

            "current_entry_rate": round(
                current_entry,
                2
            ),

            "current_exit_rate": round(
                current_exit,
                2
            ),

            "predicted_entry_rate": predicted_entry,

            "predicted_exit_rate": predicted_exit,

            "predicted_net_flow": predicted_net_flow,

            "trend": trend
        }


flow_forecast = FlowForecast()