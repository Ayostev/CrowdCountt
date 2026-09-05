# app/services/zones.py

import json
import cv2
import numpy as np


class ZoneManager:

    def __init__(self, config_path="config/zones.json"):

        self.config_path = config_path

        self.zone_polygons = {}

        # live occupancy
        self.zone_current_ids = {}

        # historical unique visitors
        self.zone_visitors = {}

        # prevents counting the same entry every frame
        self.last_seen_zone = {}
        self.zone_capacity = {}
        self.restricted_zones = set()

        # =====================================
        # ZONE TRANSITION ANALYTICS
        # =====================================
        self.track_current_zone = {}  # track_id -> current zone
        self.transition_counts = {}  # "Zone A->Zone B" -> count
        self.transition_history = []  # chronological transition log


        # 🔥 CRITICAL FIX: prevent per-frame inflation
        self.last_seen_zone = {}  # track_id → zone set

        self.load_zones()

    def load_zones(self):

        with open(self.config_path, "r") as f:
            data = json.load(f)

            # Backward compatibility
            if isinstance(data, list):
                data = data[0]

        self.zone_polygons.clear()
        self.zone_current_ids.clear()
        self.zone_visitors.clear()
        self.zone_capacity.clear()

        self.track_current_zone.clear()
        self.transition_counts.clear()
        self.transition_history.clear()
        self.restricted_zones.clear()

        for zone in data["zones"]:

            name = zone["name"]
            if zone.get("restricted", False):
                self.restricted_zones.add(name)

            capacity = zone.get("capacity", 999999)
            self.zone_capacity[name] = capacity

            polygon = np.array(zone["points"], dtype=np.int32)

            self.zone_polygons[name] = polygon
            self.zone_current_ids[name] = set()
            self.zone_visitors[name] = set()
        print("=" * 60)
        print("[ZONE MANAGER]")
        print("Zones Loaded :", len(self.zone_polygons))
        print("Restricted   :", sorted(self.restricted_zones))
        print("Capacities   :", self.zone_capacity)
        print("=" * 60)
    # =====================================
    # FIXED UPDATE (NO OVERCOUNTING)
    # =====================================
    def update(self, track_id, cx, cy):

        point = (cx, cy)

        for zone_name, polygon in self.zone_polygons.items():

            inside = cv2.pointPolygonTest(
                polygon,
                point,
                False
            ) >= 0

            if inside:

                # live occupancy
                self.zone_current_ids[zone_name].add(track_id)

                # historical visitors
                # Historical visitors
                if track_id not in self.last_seen_zone:
                    self.last_seen_zone[track_id] = set()

                if zone_name not in self.last_seen_zone[track_id]:

                    self.zone_visitors[zone_name].add(track_id)

                    # -----------------------------
                    # Transition Analytics
                    # -----------------------------
                    previous_zone = self.track_current_zone.get(track_id)

                    if previous_zone is not None and previous_zone != zone_name:
                        transition = f"{previous_zone}->{zone_name}"

                        self.transition_counts[transition] = (
                                self.transition_counts.get(transition, 0) + 1
                        )

                        self.transition_history.append({
                            "track_id": track_id,
                            "from": previous_zone,
                            "to": zone_name
                        })

                    self.track_current_zone[track_id] = zone_name

                    self.last_seen_zone[track_id].add(zone_name)

            else:

                # remove from live occupancy
                self.zone_current_ids[zone_name].discard(track_id)

                # allow future re-entry
                if track_id in self.last_seen_zone:
                    self.last_seen_zone[track_id].discard(zone_name)
    def reset(self):
        """
        IMPORTANT: DO NOT reset visitors (historical)
        ONLY reset frame logic if needed later
        """
        pass

    # =====================================
    # LIVE OCCUPANCY PER ZONE
    # =====================================
    def get_live_counts(self):

        return {
            zone: len(track_ids)
            for zone, track_ids in self.zone_current_ids.items()
        }

    # =====================================
    # HISTORICAL UNIQUE VISITORS
    # =====================================
    def get_visitors(self):

        return {
            zone: len(track_ids)
            for zone, track_ids in self.zone_visitors.items()
        }

    # =====================================
    # COMPLETE ZONE ANALYTICS
    # =====================================
    def get_zone_statistics(self):

        return {
            zone: {
                "live": len(self.zone_current_ids[zone]),
                "visitors": len(self.zone_visitors[zone])
            }
            for zone in self.zone_polygons
        }

    # =====================================
    # BACKWARD COMPATIBILITY
    # =====================================
    def get_counts(self):
        return self.get_live_counts()

    def get_capacities(self):
        return dict(self.zone_capacity)

    def get_utilization(self):

        utilization = {}

        live = self.get_live_counts()

        for zone, count in live.items():
            cap = self.zone_capacity.get(zone, 1)

            utilization[zone] = round(
                count / cap * 100,
                1
            )

        return utilization

    def get_track_zone(self, track_id):

        for zone_name, track_ids in self.zone_current_ids.items():

            if track_id in track_ids:
                return zone_name

        return None

    def get_density(self):
        density = {}
        utilization = self.get_utilization()

        for zone, percent in utilization.items():
            if percent == 0:
                level = "EMPTY"
            elif percent < 30:
                level = "LOW"
            elif percent < 60:
                level = "MODERATE"
            elif percent < 90:
                level = "HIGH"
            else:
                level = "CRITICAL"

            density[zone] = level

        return density


    def get_alerts(self):

        alerts = {}

        utilization = self.get_utilization()

        for zone, percent in utilization.items():

            if percent >= 100:

                alert = "FULL"

            elif percent >= 85:

                alert = "WARNING"

            else:

                alert = "NORMAL"

            alerts[zone] = alert

        return alerts


    def get_status(self):

        status = {}

        utilization = self.get_utilization()

        for zone, percent in utilization.items():

            if percent < 25:
                state = "EMPTY"

            elif percent < 60:
                state = "NORMAL"

            elif percent < 85:
                state = "BUSY"

            else:
                state = "FULL"

            status[zone] = state

        return status

    def get_zone_summary(self):

        live = self.get_live_counts()

        visitors = self.get_visitors()

        utilization = self.get_utilization()

        density = self.get_density()

        alerts = self.get_alerts()

        summary = {}

        for zone in self.zone_polygons:
            summary[zone] = {

                "occupancy": live[zone],

                "visitors": visitors[zone],

                "capacity": self.zone_capacity[zone],

                "utilization": utilization[zone],

                "density": density[zone],

                "alert": alerts[zone]
            }

        return summary

    # =====================================
    # TRANSITION COUNTS
    # =====================================
    def get_transition_counts(self):

        return dict(self.transition_counts)

    # =====================================
    # RESTRICTED ZONES
    # =====================================

    def get_restricted_zones(self):

        return set(self.restricted_zones)

    # =====================================
    # MOST COMMON PATHS
    # =====================================
    def get_top_transitions(self, limit=10):

        ordered = sorted(
            self.transition_counts.items(),
            key=lambda item: item[1],
            reverse=True
        )

        return [
            {
                "path": path,
                "count": count
            }
            for path, count in ordered[:limit]
        ]

    # =====================================
    # COMPLETE TRANSITION ANALYTICS
    # =====================================
    def get_transition_summary(self):

        return {
            "total_transitions": sum(
                self.transition_counts.values()
            ),

            "transition_counts": self.get_transition_counts(),

            "top_paths": self.get_top_transitions(),

            "recent_transitions": self.transition_history[-20:]
        }


    def draw(self, frame):

        for zone_name, polygon in self.zone_polygons.items():

            cv2.polylines(frame, [polygon], True, (255, 0, 255), 2)

            x, y = polygon[0]

            cv2.putText(frame, zone_name,
                        (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (255, 0, 255),
                        2)


zones = ZoneManager()