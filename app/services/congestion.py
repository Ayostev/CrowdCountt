# app/services/congestion.py

class CongestionAnalytics:

    OVERCROWD_THRESHOLD = 85.0

    def __init__(self):

        self.overcrowded_zones = set()
        self.bottlenecks = set()
        self.queues = set()

    # =====================================
    # UPDATE
    # =====================================
    def update(
        self,
        utilization,
        density,
        occupancy
    ):

        self.overcrowded_zones.clear()
        self.bottlenecks.clear()
        self.queues.clear()

        for zone in utilization:

            percent = utilization[zone]
            level = density[zone]
            count = occupancy[zone]

            # -------------------------
            # Overcrowding
            # -------------------------
            if percent >= self.OVERCROWD_THRESHOLD:

                self.overcrowded_zones.add(zone)

            # -------------------------
            # Bottleneck
            # -------------------------
            if level in (
                "HIGH",
                "CRITICAL"
            ):

                self.bottlenecks.add(zone)

            # -------------------------
            # Queue Formation
            # -------------------------
            if (
                count >= 3
                and level in (
                    "HIGH",
                    "CRITICAL"
                )
            ):

                self.queues.add(zone)

    # =====================================
    # SUMMARY
    # =====================================
    def get_summary(self):

        return {

            "overcrowded_zones": sorted(
                self.overcrowded_zones
            ),

            "bottlenecks": sorted(
                self.bottlenecks
            ),

            "queues": sorted(
                self.queues
            )
        }


congestion = CongestionAnalytics()