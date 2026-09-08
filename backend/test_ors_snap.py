import asyncio
import json
import math
import os

import httpx
from dotenv import load_dotenv


load_dotenv("backend/.env")

API_KEY = os.getenv("ORS_API_KEY")

if not API_KEY:
    raise RuntimeError("ORS_API_KEY was not found")


URL = "https://api.heigit.org/openrouteservice/v2/snap/foot-walking"


def offset_point(lat, lon, distance_m, bearing_deg):

    earth_radius = 6371000.0

    bearing = math.radians(bearing_deg)

    lat1 = math.radians(lat)
    lon1 = math.radians(lon)

    lat2 = math.asin(
        math.sin(lat1) * math.cos(distance_m / earth_radius)
        + math.cos(lat1)
        * math.sin(distance_m / earth_radius)
        * math.cos(bearing)
    )

    lon2 = lon1 + math.atan2(
        math.sin(bearing)
        * math.sin(distance_m / earth_radius)
        * math.cos(lat1),
        math.cos(distance_m / earth_radius)
        - math.sin(lat1) * math.sin(lat2),
    )

    return math.degrees(lat2), math.degrees(lon2)


async def main():

    center_lat = 12.9490
    center_lon = 77.6350

    points = []

    # Test the centre.
    points.append(
        (center_lat, center_lon, 0)
    )

    # Test rings around the destination.
    for distance in [100, 200, 300, 400, 500, 700, 1000]:

        for bearing in range(0, 360, 45):

            lat, lon = offset_point(
                center_lat,
                center_lon,
                distance,
                bearing,
            )

            points.append(
                (lat, lon, distance)
            )

    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(
        timeout=30
    ) as client:

        for lat, lon, distance in points:

            try:

                response = await client.post(
                    URL,
                    json={
                        "locations": [
                            [lon, lat]
                        ]
                    },
                    headers=headers,
                )

                data = response.json()

                location = data.get(
                    "locations",
                    [None]
                )[0]

                if location is not None:

                    print("\n================================")
                    print("✅ ORS WALKING NETWORK FOUND")
                    print("================================")

                    print(
                        "Search distance:",
                        distance,
                        "m"
                    )

                    print(
                        "Requested:",
                        lat,
                        lon
                    )

                    print(
                        "Snapped:",
                        location
                    )

                    return

            except Exception as exc:

                print(
                    "Error:",
                    exc
                )

    print("\n❌ No ORS walking network found within 1 km.")


if __name__ == "__main__":
    asyncio.run(main())