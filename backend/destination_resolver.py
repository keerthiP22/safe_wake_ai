from __future__ import annotations

import math
import os
from typing import Any

import httpx
from dotenv import load_dotenv


load_dotenv("backend/.env")

ORS_SNAP_URL = (
    "https://api.heigit.org/openrouteservice/v2/"
    "snap/foot-walking"
)

SEARCH_DISTANCES_METERS = [
    100,
    200,
    300,
    400,
    500,
    700,
    1000,
]

BEARINGS = list(range(0, 360, 45))


class DestinationResolverError(Exception):
    pass


def _offset_point(
    latitude: float,
    longitude: float,
    distance_meters: float,
    bearing_degrees: float,
) -> tuple[float, float]:

    earth_radius = 6_371_000.0

    bearing = math.radians(bearing_degrees)

    lat1 = math.radians(latitude)
    lon1 = math.radians(longitude)

    angular_distance = (
        distance_meters / earth_radius
    )

    lat2 = math.asin(
        math.sin(lat1)
        * math.cos(angular_distance)
        + math.cos(lat1)
        * math.sin(angular_distance)
        * math.cos(bearing)
    )

    lon2 = lon1 + math.atan2(
        math.sin(bearing)
        * math.sin(angular_distance)
        * math.cos(lat1),
        math.cos(angular_distance)
        - math.sin(lat1) * math.sin(lat2),
    )

    return (
        math.degrees(lat2),
        math.degrees(lon2),
    )


def _build_search_points(
    latitude: float,
    longitude: float,
) -> list[dict[str, Any]]:

    points = [
        {
            "latitude": latitude,
            "longitude": longitude,
            "search_distance": 0,
            "bearing": 0,
        }
    ]

    for distance in SEARCH_DISTANCES_METERS:

        for bearing in BEARINGS:

            point_latitude, point_longitude = _offset_point(
                latitude,
                longitude,
                distance,
                bearing,
            )

            points.append(
                {
                    "latitude": point_latitude,
                    "longitude": point_longitude,
                    "search_distance": distance,
                    "bearing": bearing,
                }
            )

    return points


async def resolve_destination(
    latitude: float,
    longitude: float,
) -> dict[str, Any]:

    api_key = os.getenv("ORS_API_KEY")

    if not api_key:
        raise DestinationResolverError(
            "ORS_API_KEY was not found in backend/.env"
        )

    search_points = _build_search_points(
        latitude,
        longitude,
    )

    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(
        timeout=30.0
    ) as client:

        for point in search_points:

            try:

                response = await client.post(
                    ORS_SNAP_URL,
                    json={
                        "locations": [
                            [
                                point["longitude"],
                                point["latitude"],
                            ]
                        ]
                    },
                    headers=headers,
                )

                if response.status_code != 200:
                    continue

                data = response.json()

                locations = data.get(
                    "locations",
                    []
                )

                if not locations:
                    continue

                snapped = locations[0]

                if snapped is None:
                    continue

                snapped_location = snapped.get(
                    "location"
                )

                if not snapped_location:
                    continue

                snapped_longitude = float(
                    snapped_location[0]
                )

                snapped_latitude = float(
                    snapped_location[1]
                )

                snapped_distance = snapped.get(
                    "snapped_distance"
                )

                print(
                    "\n=== ORS DESTINATION RESOLVED ==="
                )

                print(
                    "Requested:",
                    latitude,
                    longitude,
                )

                print(
                    "Resolved:",
                    snapped_latitude,
                    snapped_longitude,
                )

                print(
                    "Search distance:",
                    point["search_distance"],
                    "m",
                )

                print(
                    "Snapped distance:",
                    snapped_distance,
                    "m",
                )

                return {
                    "latitude": snapped_latitude,
                    "longitude": snapped_longitude,
                    "source": "ors_snap",
                    "search_distance_m": point[
                        "search_distance"
                    ],
                    "snapped_distance_m": snapped_distance,
                }

            except (
                httpx.HTTPError,
                ValueError,
                KeyError,
                TypeError,
            ):
                continue

    raise DestinationResolverError(
        "No ORS foot-walking network was found "
        "within 1 km of the selected destination."
    )


async def find_destination_candidates(
    latitude: float,
    longitude: float,
    radius_meters: float = 1000.0,
    max_candidates: int = 30,
) -> list[dict[str, Any]]:

    # Compatibility wrapper for the previous
    # candidate-based implementation.
    #
    # The new resolver uses ORS Snap directly,
    # because ORS Snap represents the actual
    # routing graph used by ORS.

    try:

        candidate = await resolve_destination(
            latitude=latitude,
            longitude=longitude,
        )

        return [candidate]

    except DestinationResolverError:
        return []
    