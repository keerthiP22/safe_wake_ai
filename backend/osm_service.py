from __future__ import annotations

from typing import Any, Iterable

import httpx


OVERPASS_URL = "https://overpass-api.de/api/interpreter"

DEFAULT_BUFFER_METERS = 40.0
MAX_ROUTE_POINTS = 25


class OSMError(Exception):
    """Raised when the Overpass API cannot provide OSM data."""


def _simplify_route_coordinates(
    coordinates: list[list[float]],
    max_points: int = MAX_ROUTE_POINTS,
) -> list[list[float]]:
    if len(coordinates) <= max_points:
        return coordinates

    step = (len(coordinates) - 1) / (max_points - 1)

    simplified = []

    for index in range(max_points):
        source_index = round(index * step)
        simplified.append(coordinates[source_index])

    return simplified


def _build_linestring_query_points(
    geometry: dict[str, Any],
) -> str:

    coordinates = geometry.get("coordinates")

    if not isinstance(coordinates, list):
        raise OSMError(
            "Route geometry does not contain coordinates."
        )

    usable_coordinates: list[list[float]] = []

    for coordinate in coordinates:

        if (
            isinstance(coordinate, list)
            and len(coordinate) >= 2
        ):

            longitude = coordinate[0]
            latitude = coordinate[1]

            if (
                isinstance(longitude, (int, float))
                and isinstance(latitude, (int, float))
            ):

                usable_coordinates.append(
                    [
                        float(longitude),
                        float(latitude),
                    ]
                )

    if len(usable_coordinates) < 2:
        raise OSMError(
            "Route geometry contains insufficient coordinates."
        )

    usable_coordinates = _simplify_route_coordinates(
        usable_coordinates
    )

    # Overpass around-linestring expects:
    # latitude,longitude
    points = []

    for longitude, latitude in usable_coordinates:

        points.append(
            f"{latitude:.7f},{longitude:.7f}"
        )

    return ",".join(points)


def _build_overpass_query(
    geometry: dict[str, Any],
    buffer_meters: float,
) -> str:

    line_points = _build_linestring_query_points(
        geometry
    )

    return f"""
[out:json][timeout:60];

(
  /* All highway ways near the route */
  way["highway"]
    (around:{buffer_meters},{line_points});

  /* Crossing nodes */
  node["highway"="crossing"]
    (around:{buffer_meters},{line_points});

  /* Dedicated crossing ways */
  way["highway"="footway"]["footway"="crossing"]
    (around:{buffer_meters},{line_points});

  /* Pedestrian infrastructure */
  way["highway"="path"]
    (around:{buffer_meters},{line_points});

  way["highway"="pedestrian"]
    (around:{buffer_meters},{line_points});

  way["highway"="footway"]
    (around:{buffer_meters},{line_points});

  /* Street lamps */
  node["highway"="street_lamp"]
    (around:{buffer_meters},{line_points});

  /* Explicitly lit features */
  way["highway"]["lit"]
    (around:{buffer_meters},{line_points});
);

/* IMPORTANT:
   geom gives us the complete geometry of each way.
   This lets us inspect actual OSM connectivity. */
out body geom;
"""


async def query_route_features(
    geometry: dict[str, Any],
    buffer_meters: float = DEFAULT_BUFFER_METERS,
) -> dict[str, Any]:

    query = _build_overpass_query(
        geometry=geometry,
        buffer_meters=buffer_meters,
    )

    headers = {
        "User-Agent": (
            "SafeWalkAI/0.1 "
            "(student pedestrian safety routing project)"
        ),
    }

    try:

        async with httpx.AsyncClient(
            timeout=75.0
        ) as client:

            response = await client.post(
                OVERPASS_URL,
                data={"data": query},
                headers=headers,
            )

    except httpx.RequestError as exc:

        raise OSMError(
            f"Could not connect to Overpass API: {exc}"
        ) from exc

    if response.status_code != 200:

        raise OSMError(
            f"Overpass returned HTTP {response.status_code}."
        )

    try:

        data = response.json()

    except ValueError as exc:

        raise OSMError(
            "Overpass returned invalid JSON."
        ) from exc

    elements = data.get("elements", [])

    if not isinstance(elements, list):

        raise OSMError(
            "Overpass returned an unexpected response structure."
        )

    return {
        "element_count": len(elements),
        "elements": elements,
    }


def _string_to_float(
    value: Any,
) -> float | None:

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):

        try:

            return float(
                value.strip().split()[0]
            )

        except (ValueError, IndexError):

            return None

    return None


def _is_truthy_osm_value(
    value: Any,
) -> bool:

    if value is None:
        return False

    value_text = str(value).strip().lower()

    return value_text not in {
        "",
        "no",
        "none",
        "false",
        "0",
    }


def _classify_road_type(
    highway: str | None,
) -> str:

    if not highway:
        return "unknown"

    major_roads = {
        "motorway",
        "motorway_link",
        "trunk",
        "trunk_link",
        "primary",
        "primary_link",
    }

    secondary_roads = {
        "secondary",
        "secondary_link",
        "tertiary",
        "tertiary_link",
    }

    local_roads = {
        "residential",
        "living_street",
        "unclassified",
        "service",
    }

    pedestrian_types = {
        "footway",
        "path",
        "pedestrian",
        "steps",
        "crossing",
        "corridor",
    }

    if highway in major_roads:
        return "major"

    if highway in secondary_roads:
        return "secondary"

    if highway in local_roads:
        return "local"

    if highway in pedestrian_types:
        return "pedestrian"

    return "other"


def extract_route_features(
    overpass_data: dict[str, Any],
) -> dict[str, Any]:

    elements = overpass_data.get(
        "elements",
        [],
    )

    road_ways = []
    pedestrian_ways = []
    crossing_nodes = []
    crossing_ways = []

    street_lamps = []
    lit_features = []

    road_widths: list[float] = []

    road_types: dict[str, int] = {}

    surface_types: dict[str, int] = {}

    foot_access_types: dict[str, int] = {}

    sidewalk_yes = 0
    sidewalk_separate = 0
    sidewalk_no = 0
    sidewalk_unknown = 0

    # ---------------------------------------------------------
    # PROCESS OSM ELEMENTS
    # ---------------------------------------------------------

    for element in elements:

        tags = element.get(
            "tags",
            {}
        )

        if not isinstance(tags, dict):
            continue

        highway = tags.get("highway")

        # -----------------------------------------------------
        # STREET LAMPS
        # -----------------------------------------------------

        if highway == "street_lamp":

            street_lamps.append(element)

        # -----------------------------------------------------
        # EXPLICIT LIGHTING
        # -----------------------------------------------------

        if "lit" in tags:

            lit_features.append(element)

        # -----------------------------------------------------
        # SURFACE
        # -----------------------------------------------------

        surface = tags.get("surface")

        if surface:

            surface_types[surface] = (
                surface_types.get(
                    surface,
                    0,
                )
                + 1
            )

        # -----------------------------------------------------
        # FOOT ACCESS
        # -----------------------------------------------------

        foot_access = tags.get("foot")

        if foot_access:

            foot_access_types[foot_access] = (
                foot_access_types.get(
                    foot_access,
                    0,
                )
                + 1
            )

        # -----------------------------------------------------
        # PEDESTRIAN WAYS
        # -----------------------------------------------------

        if highway in {
            "footway",
            "path",
            "pedestrian",
        }:

            pedestrian_ways.append(element)

        # -----------------------------------------------------
        # CROSSINGS
        # -----------------------------------------------------

        if highway == "crossing":

            crossing_nodes.append(element)

        if (
            highway == "footway"
            and tags.get("footway") == "crossing"
        ):

            crossing_ways.append(element)

        # -----------------------------------------------------
        # ROAD WAYS
        # -----------------------------------------------------

        if highway in {
            "motorway",
            "motorway_link",
            "trunk",
            "trunk_link",
            "primary",
            "primary_link",
            "secondary",
            "secondary_link",
            "tertiary",
            "tertiary_link",
            "residential",
            "living_street",
            "unclassified",
            "service",
        }:

            road_ways.append(element)

            road_type = _classify_road_type(
                highway
            )

            road_types[road_type] = (
                road_types.get(
                    road_type,
                    0,
                )
                + 1
            )

            # -------------------------------------------------
            # WIDTH
            # -------------------------------------------------

            width = _string_to_float(
                tags.get("width")
            )

            if (
                width is not None
                and width > 0
            ):

                road_widths.append(width)

            # -------------------------------------------------
            # SIDEWALK
            # -------------------------------------------------

            sidewalk = tags.get(
                "sidewalk"
            )

            if sidewalk in {
                "both",
                "left",
                "right",
                "yes",
            }:

                sidewalk_yes += 1

            elif sidewalk == "separate":

                sidewalk_separate += 1

            elif sidewalk == "no":

                sidewalk_no += 1

            else:

                sidewalk_unknown += 1

    # =========================================================
    # CROSSINGS
    # =========================================================

    crossing_count = (
        len(crossing_nodes)
        + len(crossing_ways)
    )

    # =========================================================
    # SIDEWALK
    # =========================================================

    sidewalk_known_count = (
        sidewalk_yes
        + sidewalk_separate
        + sidewalk_no
    )

    if sidewalk_known_count > 0:

        sidewalk_coverage = (
            sidewalk_yes
            + sidewalk_separate
        ) / sidewalk_known_count

    else:

        sidewalk_coverage = None

    # =========================================================
    # PEDESTRIAN PATH COVERAGE
    # =========================================================

    pedestrian_path_count = len(
        pedestrian_ways
    )

    if road_ways:

        pedestrian_path_coverage = (
            pedestrian_path_count
            / (
                pedestrian_path_count
                + len(road_ways)
            )
        )

    else:

        pedestrian_path_coverage = (
            1.0
            if pedestrian_path_count > 0
            else None
        )

    # =========================================================
    # INTERSECTIONS
    # =========================================================

    intersection_count = (
        _estimate_intersections(
            road_ways
        )
    )

    # =========================================================
    # WIDTH
    # =========================================================

    mean_width = (
        sum(road_widths)
        / len(road_widths)
        if road_widths
        else None
    )

    max_width = (
        max(road_widths)
        if road_widths
        else None
    )

    # =========================================================
    # RETURN FEATURES
    # =========================================================

    return {

        "sidewalk_coverage":
            sidewalk_coverage,

        "pedestrian_path_coverage":
            pedestrian_path_coverage,

        "crossing_count":
            crossing_count,

        "road_type_distribution":
            road_types,

        "intersection_count":
            intersection_count,

        "road_width_mean_m":
            mean_width,

        "road_width_max_m":
            max_width,

        "street_lamp_count":
            len(street_lamps),

        "lit_feature_count":
            len(lit_features),

        "surface_distribution":
            surface_types,

        "foot_access_distribution":
            foot_access_types,

        "osm_counts": {

            "road_ways":
                len(road_ways),

            "pedestrian_ways":
                len(pedestrian_ways),

            "crossing_nodes":
                len(crossing_nodes),

            "crossing_ways":
                len(crossing_ways),

        },

        "sidewalk_data_quality": {

            "known":
                sidewalk_known_count,

            "unknown":
                sidewalk_unknown,

        },
    }


def _estimate_intersections(
    road_ways: Iterable[dict[str, Any]],
) -> int:

    """
    Estimate intersections using actual OSM way node
    connectivity.

    A node shared by three or more road ways is treated
    as an intersection.
    """

    node_usage: dict[int, int] = {}

    for way in road_ways:

        nodes = way.get(
            "nodes"
        )

        if not isinstance(
            nodes,
            list,
        ):

            continue

        for node_id in nodes:

            if isinstance(
                node_id,
                int,
            ):

                node_usage[node_id] = (
                    node_usage.get(
                        node_id,
                        0,
                    )
                    + 1
                )

    return sum(
        1
        for usage_count
        in node_usage.values()
        if usage_count >= 3
    )