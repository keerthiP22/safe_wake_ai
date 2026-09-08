import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE)

ORS_DIRECTIONS_URL = (
    "https://api.openrouteservice.org/v2/directions/foot-walking/geojson"
)

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"

USER_AGENT = "SafeWalkAI/0.1 (student pedestrian safety routing project)"


class ORSError(Exception):
    """Raised when an external routing/geocoding service fails."""


def get_ors_api_key() -> str:
    """Load the ORS API key from backend/.env."""

    api_key = os.getenv("ORS_API_KEY")

    if not api_key:
        raise ORSError(
            f"ORS_API_KEY is not configured. Expected it in: {ENV_FILE}"
        )

    return api_key


async def get_walking_routes(
    start_latitude: float,
    start_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
) -> dict[str, Any]:
    """Get multiple real walking routes from OpenRouteService."""

    api_key = get_ors_api_key()

    payload = {
        "coordinates": [
            [start_longitude, start_latitude],
            [destination_longitude, destination_latitude],
        ],

        "instructions": True,

        "units": "m",

        # Ask ORS for alternative walking routes.
        "alternative_routes": {
            "target_count": 3,
            "weight_factor": 1.6,
            "share_factor": 0.6,
        },
    }

    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
        "Accept": "application/geo+json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                ORS_DIRECTIONS_URL,
                json=payload,
                headers=headers,
            )

    except httpx.RequestError as exc:
        raise ORSError(
            f"Could not connect to ORS routing service: {exc}"
        ) from exc

    try:
        data = response.json()

    except ValueError as exc:
        raise ORSError(
            "ORS routing service returned invalid JSON."
        ) from exc

    if response.status_code != 200:

        error_data = data.get("error", {})

        if isinstance(error_data, dict):
            message = error_data.get("message")
        else:
            message = None

        message = message or data.get(
            "message",
            "ORS routing request failed.",
        )

        raise ORSError(
            f"ORS routing returned HTTP {response.status_code}: {message}"
        )

    return data


async def search_places(
    query: str,
    size: int = 8,
) -> list[dict[str, Any]]:
    """
    Search real places using OpenStreetMap Nominatim.

    The search is restricted to India and returns POI/address
    information suitable for a Maps-style location picker.
    """

    query = query.strip()

    if not query:
        return []

    size = min(max(size, 1), 10)

    params = {
        "q": query,
        "format": "jsonv2",
        "limit": size,
        "countrycodes": "in",
        "addressdetails": 1,
        "namedetails": 1,
        "dedupe": 1,
        "accept-language": "en",
    }

    headers = {
        "User-Agent": USER_AGENT,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                NOMINATIM_SEARCH_URL,
                params=params,
                headers=headers,
            )

    except httpx.RequestError as exc:
        raise ORSError(
            f"Could not connect to OpenStreetMap geocoding: {exc}"
        ) from exc

    try:
        data = response.json()

    except ValueError as exc:
        raise ORSError(
            "OpenStreetMap geocoding returned invalid JSON."
        ) from exc

    if response.status_code != 200:
        raise ORSError(
            f"OpenStreetMap geocoding returned HTTP {response.status_code}."
        )

    results: list[dict[str, Any]] = []

    for item in data:

        try:
            latitude = float(item["lat"])
            longitude = float(item["lon"])

        except (KeyError, TypeError, ValueError):
            continue

        address = item.get("address", {})

        results.append(
            {
                "place_name": item.get(
                    "display_name",
                    query,
                ),
                "latitude": latitude,
                "longitude": longitude,
                "type": item.get("type"),
                "category": item.get("category"),
                "city": (
                    address.get("city")
                    or address.get("town")
                    or address.get("municipality")
                ),
                "state": address.get("state"),
                "country": address.get("country"),
                "postcode": address.get("postcode"),
            }
        )

    return results


async def reverse_geocode(
    latitude: float,
    longitude: float,
) -> dict[str, Any]:
    """Convert coordinates into a human-readable place."""

    params = {
        "lat": latitude,
        "lon": longitude,
        "format": "jsonv2",
        "addressdetails": 1,
        "zoom": 18,
        "accept-language": "en",
    }

    headers = {
        "User-Agent": USER_AGENT,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                NOMINATIM_REVERSE_URL,
                params=params,
                headers=headers,
            )

    except httpx.RequestError as exc:
        raise ORSError(
            f"Could not connect to OpenStreetMap reverse geocoding: {exc}"
        ) from exc

    try:
        data = response.json()

    except ValueError as exc:
        raise ORSError(
            "OpenStreetMap reverse geocoding returned invalid JSON."
        ) from exc

    if response.status_code != 200:
        raise ORSError(
            "OpenStreetMap reverse geocoding request failed."
        )

    if not data:
        raise ORSError(
            "No place information was found for these coordinates."
        )

    address = data.get("address", {})

    return {
        "place_name": data.get("display_name"),
        "latitude": latitude,
        "longitude": longitude,
        "type": data.get("type"),
        "category": data.get("category"),
        "city": (
            address.get("city")
            or address.get("town")
            or address.get("municipality")
        ),
        "state": address.get("state"),
        "country": address.get("country"),
        "postcode": address.get("postcode"),
        "road": address.get("road"),
        "neighbourhood": address.get("neighbourhood"),
        "suburb": address.get("suburb"),
    }