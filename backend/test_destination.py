import asyncio

from backend.destination_resolver import find_destination_candidates
from backend.ors_service import get_walking_routes, ORSError


async def main():

    start_latitude = 12.9352
    start_longitude = 77.6245

    candidates = await find_destination_candidates(
        latitude=12.9490,
        longitude=77.6350,
        radius_meters=1000,
        max_candidates=30,
    )

    print(f"\nTesting {len(candidates)} candidates against ORS...\n")

    for index, candidate in enumerate(candidates, start=1):

        latitude = candidate["latitude"]
        longitude = candidate["longitude"]

        try:

            result = await get_walking_routes(
                start_latitude=start_latitude,
                start_longitude=start_longitude,
                destination_latitude=latitude,
                destination_longitude=longitude,
            )

            route_count = len(
                result.get("features", [])
            )

            print(
                f"✅ CANDIDATE {index} WORKS"
            )

            print(
                f"   Coordinates: "
                f"{latitude}, {longitude}"
            )

            print(
                f"   Distance from destination: "
                f"{candidate['distance']} m"
            )

            print(
                f"   Highway: "
                f"{candidate.get('highway')}"
            )

            print(
                f"   Source: "
                f"{candidate.get('source')}"
            )

            print(
                f"   ORS routes: "
                f"{route_count}"
            )

            print()

            # Stop at the first working candidate.
            break

        except ORSError as error:

            print(
                f"❌ Candidate {index}: "
                f"{latitude}, {longitude} "
                f"| {candidate['distance']} m "
                f"| {candidate.get('highway')} "
                f"| rejected"
            )


if __name__ == "__main__":
    asyncio.run(main())