import asyncio

from backend.osm_service import (
    extract_route_features,
    query_route_features,
)


TEST_GEOMETRY = {
    "type": "LineString",
    "coordinates": [
        [77.6408, 12.9784],
        [77.6395, 12.9780],
        [77.6380, 12.9775],
    ],
}


async def main() -> None:
    raw = await query_route_features(TEST_GEOMETRY)

    print("Raw OSM elements:", raw["element_count"])

    features = extract_route_features(raw)

    print("\nExtracted features:")

    for key, value in features.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())