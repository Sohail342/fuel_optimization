import math
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests
from django.contrib.gis.geos import LineString
from django.contrib.gis.measure import Distance
from django.utils import timezone

from apps.fuel.models import FuelStation, RouteCache
from apps.fuel.utils.normalizer import normalizer


class RoutingService:
    # Only load stations within this corridor of the route
    STATION_CORRIDOR_MILES = 15.0
    CACHE_TTL_DAYS = 7

    def get_cached_route(self, start: str, end: str) -> Optional[RouteCache]:
        """Return a cached route only if it was refreshed within the TTL window."""
        start_location = normalizer(start)
        destination = normalizer(end)
        cutoff = timezone.now() - timedelta(days=self.CACHE_TTL_DAYS)

        try:
            return RouteCache.objects.filter(
                start=start_location,
                destination=destination,
                updated_at__gte=cutoff,
            ).first()
        except Exception:
            return None

    def save_cached_route(
        self,
        start: str,
        end: str,
        route_coordinates: List[List[float]],
        distance_miles: float,
        duration_seconds: int,
    ) -> None:
        try:
            RouteCache.objects.update_or_create(
                start=normalizer(start),
                destination=normalizer(end),
                defaults={
                    "route": LineString([tuple(point) for point in route_coordinates]),
                    "distance_miles": distance_miles,
                    "duration_seconds": duration_seconds,
                },
            )
        except Exception:
            pass

    def route_payload_from_cache(self, cached: RouteCache) -> Dict[str, Any]:
        coordinates = [[float(lon), float(lat)] for lon, lat in cached.route.coords]
        return {
            "geometry": {"type": "LineString", "coordinates": coordinates},
            "coordinates": coordinates,
            "distance_miles": cached.distance_miles,
            "duration_seconds": cached.duration_seconds,
        }

    def plan_trip(
        self,
        start: str,
        end: str,
        max_range_miles: float = 500.0,
        miles_per_gallon: float = 10.0,
    ) -> Dict[str, Any]:
        cached = self.get_cached_route(start, end)

        if cached:
            route_response = self.route_payload_from_cache(cached)
            route_coordinates = route_response["coordinates"]
            start_coords = (route_coordinates[0][1], route_coordinates[0][0])
            end_coords = (route_coordinates[-1][1], route_coordinates[-1][0])
        else:
            start_coords = self.geocode_location(start)
            end_coords = self.geocode_location(end)
            route_response = self.get_route_geometry(start_coords, end_coords)
            route_coordinates = route_response["coordinates"]
            self.save_cached_route(
                start=start,
                end=end,
                route_coordinates=route_coordinates,
                distance_miles=route_response["distance_miles"],
                duration_seconds=route_response["duration_seconds"],
            )

        fuel_plan = self.build_fuel_plan(
            route_coordinates=route_coordinates,
            stations=self.load_station_data(route_coordinates),
            max_range_miles=max_range_miles,
            miles_per_gallon=miles_per_gallon,
        )

        return {
            "start": start,
            "destination": end,
            "route": {
                "geometry": route_response["geometry"],
                "distance_miles": round(route_response["distance_miles"], 2),
                "duration_minutes": round(route_response["duration_seconds"] / 60, 1),
                "map_url": self.build_map_url(start_coords, end_coords),
            },
            "fuel_plan": fuel_plan,
        }

    def geocode_location(self, location: str) -> Tuple[float, float]:
        try:
            response = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": location,
                    "format": "jsonv2",
                    "limit": 1,
                    "addressdetails": 1,
                    "countrycodes": "us",
                },
                headers={"User-Agent": "fuel-assessment/1.0"},
                timeout=10,
            )
            response.raise_for_status()
            results = response.json()
        except requests.RequestException as exc:
            raise ValueError(f"Unable to geocode location: {location}") from exc

        if not results:
            raise ValueError(f"Unable to geocode location: {location}")

        result = results[0]
        if result.get("address", {}).get("country_code") != "us":
            raise ValueError(f"Location must be within the USA: {location}")

        return float(result["lat"]), float(result["lon"])

    def get_route_geometry(
        self,
        start_coords: Tuple[float, float],
        end_coords: Tuple[float, float],
    ) -> Dict[str, Any]:
        start_lat, start_lon = start_coords
        end_lat, end_lon = end_coords

        try:
            response = requests.get(
                "https://router.project-osrm.org/route/v1/driving/"
                f"{start_lon},{start_lat};{end_lon},{end_lat}"
                "?overview=simplified&geometries=geojson",
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise ValueError(
                "Unable to compute a driving route for the supplied locations"
            ) from exc

        if payload.get("code") not in (None, "Ok") or not payload.get("routes"):
            raise ValueError(
                "Unable to compute a driving route for the supplied locations"
            )

        route = payload["routes"][0]
        geometry = route["geometry"]
        coordinates = geometry.get("coordinates", [])
        if not coordinates:
            raise ValueError("Routing service did not return any geometry")

        distance_miles = route["distance"] / 1609.344
        duration_seconds = int(route["duration"])

        return {
            "geometry": geometry,
            "coordinates": [[float(lon), float(lat)] for lon, lat in coordinates],
            "distance_miles": distance_miles,
            "duration_seconds": duration_seconds,
        }

    def load_station_data(
        self,
        route_coordinates: List[List[float]],
        corridor_miles: float = STATION_CORRIDOR_MILES,
    ) -> List[Dict[str, Any]]:
        """Load only stations within a PostGIS corridor around the route."""
        if len(route_coordinates) < 2:
            return []

        route_line = LineString(
            [tuple(point) for point in route_coordinates],
            srid=4326,
        )

        try:
            stations = list(
                FuelStation.objects.filter(
                    location__dwithin=(route_line, Distance(mi=corridor_miles)),
                ).values(
                    "truckstop_name",
                    "address",
                    "city",
                    "state",
                    "retail_price",
                    "location",
                )
            )
        except Exception:
            return []

        return [
            {
                "name": station["truckstop_name"],
                "address": station["address"],
                "city": station["city"],
                "state": station["state"],
                "retail_price": float(station["retail_price"]),
                "latitude": self._extract_latitude(station["location"]),
                "longitude": self._extract_longitude(station["location"]),
            }
            for station in stations
        ]

    def build_fuel_plan(
        self,
        route_coordinates: List[List[float]],
        stations: List[Dict[str, Any]],
        max_range_miles: float = 500.0,
        miles_per_gallon: float = 10.0,
    ) -> Dict[str, Any]:
        if not route_coordinates:
            return {
                "fuel_stops": [],
                "total_fuel_cost": 0.0,
                "total_fuel_needed_gallons": 0.0,
                "route_distance_miles": 0.0,
            }

        projected_stations = []
        for station in stations:
            if station.get("latitude") is None or station.get("longitude") is None:
                continue
            projected_mile = self._project_point_to_route(
                station["latitude"],
                station["longitude"],
                route_coordinates,
            )
            projected_stations.append(
                {**station, "projected_route_mile": projected_mile}
            )

        route_distance_miles = self._calculate_route_distance(route_coordinates)
        fuel_stops: List[Dict[str, Any]] = []
        total_cost = 0.0
        current_progress = 0.0

        while current_progress < route_distance_miles - 1e-9:
            segment_end = min(current_progress + max_range_miles, route_distance_miles)
            segment_distance = segment_end - current_progress
            candidates = [
                station
                for station in projected_stations
                if current_progress <= station["projected_route_mile"] <= segment_end
            ]

            if not candidates:
                current_progress = segment_end
                continue

            cheapest = min(candidates, key=lambda station: station["retail_price"])
            gallons_needed = segment_distance / miles_per_gallon
            segment_cost = gallons_needed * cheapest["retail_price"]
            total_cost += segment_cost

            fuel_stops.append(
                {
                    "name": cheapest["name"],
                    "city": cheapest["city"],
                    "state": cheapest["state"],
                    "price_per_gallon": round(cheapest["retail_price"], 3),
                    "route_mile": round(cheapest["projected_route_mile"], 2),
                    "distance_from_previous_stop_miles": round(
                        max(0.0, cheapest["projected_route_mile"] - current_progress),
                        2,
                    ),
                    "gallons_needed": round(gallons_needed, 2),
                    "estimated_cost": round(segment_cost, 2),
                }
            )
            current_progress = segment_end

        return {
            "fuel_stops": fuel_stops,
            "total_fuel_cost": round(total_cost, 2),
            "total_fuel_needed_gallons": round(
                route_distance_miles / miles_per_gallon, 2
            ),
            "route_distance_miles": round(route_distance_miles, 2),
        }

    def _calculate_route_distance(self, route_coordinates: List[List[float]]) -> float:
        total = 0.0
        for index in range(1, len(route_coordinates)):
            previous = route_coordinates[index - 1]
            current = route_coordinates[index]
            total += self._haversine_miles(
                previous[1], previous[0], current[1], current[0]
            )
        return total

    def _project_point_to_route(
        self,
        latitude: float,
        longitude: float,
        route_coordinates: List[List[float]],
    ) -> float:
        if not route_coordinates:
            return 0.0

        total = 0.0
        minimum_distance = float("inf")
        best_distance = 0.0

        for index in range(1, len(route_coordinates)):
            previous = route_coordinates[index - 1]
            current = route_coordinates[index]
            segment_distance = self._haversine_miles(
                previous[1], previous[0], current[1], current[0]
            )
            if segment_distance == 0:
                current_distance = self._haversine_miles(
                    latitude, longitude, previous[1], previous[0]
                )
                if current_distance < minimum_distance:
                    minimum_distance = current_distance
                    best_distance = total
                continue

            projected_distance = self._project_point_to_segment(
                latitude,
                longitude,
                previous[1],
                previous[0],
                current[1],
                current[0],
            )
            if projected_distance < minimum_distance:
                minimum_distance = projected_distance
                best_distance = total + self._distance_along_segment(
                    previous[1],
                    previous[0],
                    current[1],
                    current[0],
                    latitude,
                    longitude,
                )
            total += segment_distance

        return best_distance

    def _project_point_to_segment(
        self,
        lat: float,
        lon: float,
        seg_lat1: float,
        seg_lon1: float,
        seg_lat2: float,
        seg_lon2: float,
    ) -> float:
        return self._haversine_miles(
            lat,
            lon,
            self._interpolate_latitude(seg_lat1, seg_lat2),
            self._interpolate_longitude(seg_lon1, seg_lon2),
        )

    def _distance_along_segment(
        self,
        seg_lat1: float,
        seg_lon1: float,
        seg_lat2: float,
        seg_lon2: float,
        lat: float,
        lon: float,
    ) -> float:
        segment_distance = self._haversine_miles(seg_lat1, seg_lon1, seg_lat2, seg_lon2)
        if segment_distance == 0:
            return 0.0
        start_distance = self._haversine_miles(seg_lat1, seg_lon1, lat, lon)
        end_distance = self._haversine_miles(seg_lat2, seg_lon2, lat, lon)
        return min(start_distance, end_distance)

    def _interpolate_latitude(self, lat1: float, lat2: float) -> float:
        return (lat1 + lat2) / 2.0

    def _interpolate_longitude(self, lon1: float, lon2: float) -> float:
        return (lon1 + lon2) / 2.0

    def _haversine_miles(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        earth_radius_miles = 3958.8
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        delta_lat = lat2_rad - lat1_rad
        delta_lon = lon2_rad - lon1_rad
        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return earth_radius_miles * c

    def build_map_url(
        self, start_coords: Tuple[float, float], end_coords: Tuple[float, float]
    ) -> str:
        start_lat, start_lon = start_coords
        end_lat, end_lon = end_coords
        return (
            "https://www.openstreetmap.org/directions?engine=osrm_car"
            f"&route={start_lat},{start_lon};{end_lat},{end_lon}"
        )

    def _extract_latitude(self, location: Any) -> Optional[float]:
        if not location:
            return None
        if hasattr(location, "x"):
            return float(location.y)
        return None

    def _extract_longitude(self, location: Any) -> Optional[float]:
        if not location:
            return None
        if hasattr(location, "x"):
            return float(location.x)
        return None
