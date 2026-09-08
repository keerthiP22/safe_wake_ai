"""FastAPI backend for the Safe Pedestrian Route project."""

from typing import Any
import json
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.ml_service import predict_safety

from backend.ors_service import (
    ORSError,
    get_walking_routes,
    reverse_geocode,
    search_places,
)

from backend.osm_service import (
    OSMError,
    extract_route_features,
    query_route_features,
)
from backend.destination_resolver import (
    DestinationResolverError,
    find_destination_candidates,
)


app = FastAPI(
    title="Safe Pedestrian Route API",
    version="0.5.0",
    description="Backend for real pedestrian route recommendations.",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class Coordinates(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class RouteRequest(BaseModel):
    start: Coordinates
    destination: Coordinates


@app.get("/api/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "safe-walk-ai-backend",
    }


@app.get("/api/search", tags=["search"])
async def search_places_endpoint(
    q: str = Query(
        min_length=1,
        max_length=200,
        description="Place name or address to search for",
    ),
) -> dict[str, Any]:

    try:
        places = await search_places(q)

    except ORSError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    return {
        "status": "ok",
        "query": q,
        "results": places,
    }


@app.get("/api/reverse", tags=["search"])
async def reverse_geocode_endpoint(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
) -> dict[str, Any]:

    try:
        place = await reverse_geocode(
            latitude=latitude,
            longitude=longitude,
        )

    except ORSError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    return {
        "status": "ok",
        "result": place,
    }


@app.post("/api/routes", tags=["routes"])
async def get_routes(
    request: RouteRequest,
) -> dict[str, Any]:

    if (
        request.start.latitude == request.destination.latitude
        and request.start.longitude == request.destination.longitude
    ):
        raise HTTPException(
            status_code=400,
            detail="Start and destination cannot be the same.",
        )

    # ---------------------------------------------------------
    # GET ORS ROUTES
    # ---------------------------------------------------------

        # ---------------------------------------------------------
    # GET ORS ROUTES
    # ---------------------------------------------------------

    destination_latitude = request.destination.latitude
    destination_longitude = request.destination.longitude

    destination_adjusted = False
    resolved_destination = None

    try:
        # First try the exact destination selected by the user.
        ors_data = await get_walking_routes(
            start_latitude=request.start.latitude,
            start_longitude=request.start.longitude,
            destination_latitude=destination_latitude,
            destination_longitude=destination_longitude,
        )

    except ORSError as original_ors_error:

        # ---------------------------------------------------------
        # DESTINATION FALLBACK
        # ---------------------------------------------------------
        # If ORS cannot route directly to the selected destination,
        # search nearby OSM walkable ways/nodes and try them one by one.

        try:
            candidates = await find_destination_candidates(
                latitude=request.destination.latitude,
                longitude=request.destination.longitude,
            )

        except DestinationResolverError as resolver_error:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": (
                        "The selected destination is not directly "
                        "walkable/routable, and nearby OSM access "
                        "points could not be found."
                    ),
                    "original_error": str(original_ors_error),
                    "resolver_error": str(resolver_error),
                },
            ) from resolver_error

        ors_data = None
        last_ors_error = original_ors_error

        # Try nearby candidates until ORS accepts one.
        for candidate in candidates:
            try:
                candidate_ors_data = await get_walking_routes(
                    start_latitude=request.start.latitude,
                    start_longitude=request.start.longitude,
                    destination_latitude=candidate["latitude"],
                    destination_longitude=candidate["longitude"],
                )

                # Successful candidate found.
                ors_data = candidate_ors_data
                destination_latitude = candidate["latitude"]
                destination_longitude = candidate["longitude"]
                destination_adjusted = True
                resolved_destination = candidate

                print("\n=== DESTINATION RESOLVED ===")
                print(
                    f"Requested: {request.destination.latitude}, "
                    f"{request.destination.longitude}"
                )
                print(
                    f"Resolved: {destination_latitude}, "
                    f"{destination_longitude}"
                )
                print(f"Source: {candidate.get('source')}")
                print(f"Distance: {candidate.get('distance')} m")
                break

            except ORSError as candidate_error:
                last_ors_error = candidate_error
                continue

        if ors_data is None:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": (
                        "The selected destination is not directly "
                        "walkable/routable, and no nearby walkable "
                        "access point could be routed to."
                    ),
                    "original_error": str(original_ors_error),
                    "last_candidate_error": str(last_ors_error),
                    "candidate_count": len(candidates),
                },
            ) from last_ors_error

    features = ors_data.get("features", [])

    if not features:
        raise HTTPException(
            status_code=404,
            detail="ORS returned no walking route.",
        )

    routes = []

    # =========================================================
    # PROCESS EACH ROUTE
    # =========================================================

    for index, feature in enumerate(features):

        properties = feature.get("properties", {})
        summary = properties.get("summary", {})
        geometry = feature.get("geometry")

        if not geometry:
            raise HTTPException(
                status_code=502,
                detail=f"Route {index + 1} has no geometry.",
            )

        try:

            # -------------------------------------------------
            # OSM
            # -------------------------------------------------

            raw_osm = await query_route_features(
                geometry=geometry,
            )

            osm_features = extract_route_features(
                raw_osm
            )

            # -------------------------------------------------
            # ROAD TYPES
            # -------------------------------------------------

            road_types = osm_features.get(
                "road_type_distribution",
                {},
            )

            major_count = road_types.get("major", 0)
            secondary_count = road_types.get("secondary", 0)
            local_count = road_types.get("local", 0)
            pedestrian_count = road_types.get("pedestrian", 0)

            total_roads = (
                major_count
                + secondary_count
                + local_count
                + pedestrian_count
            )

            if total_roads > 0:

                road_type_score = (
                    1.0 * pedestrian_count
                    + 0.85 * local_count
                    + 0.65 * secondary_count
                    + 0.30 * major_count
                ) / total_roads

            else:

                road_type_score = 0.5

            # -------------------------------------------------
            # CROSSINGS
            # -------------------------------------------------

            crossing_count = (
                osm_features.get("crossing_count")
                or 0
            )

            road_count = (
                osm_features
                .get("osm_counts", {})
                .get("road_ways", 0)
            )

            if road_count > 0:

                crossing_density = min(
                    crossing_count / road_count,
                    1.0,
                )

            else:

                crossing_density = 0.0

            # -------------------------------------------------
            # WIDTH
            # -------------------------------------------------

            width = osm_features.get(
                "road_width_mean_m"
            )

            if width is None:

                width_score = 0.5

            elif width <= 3:

                width_score = 1.0

            elif width >= 12:

                width_score = 0.2

            else:

                width_score = (
                    1.0
                    - ((width - 3) / 9) * 0.8
                )

            # -------------------------------------------------
            # SIDEWALK
            # -------------------------------------------------

            sidewalk_coverage = osm_features.get(
                "sidewalk_coverage"
            )

            if sidewalk_coverage is None:

                sidewalk_score = 0.5
                sidewalk_known = 0

            else:

                sidewalk_score = sidewalk_coverage
                sidewalk_known = 1

            sidewalk_positive = (
                1
                if sidewalk_score >= 0.8
                else 0
            )

            # -------------------------------------------------
            # PEDESTRIAN PATH
            # -------------------------------------------------

            pedestrian_path_coverage = (
                osm_features.get(
                    "pedestrian_path_coverage"
                )
            )

            if pedestrian_path_coverage is None:
                pedestrian_path_coverage = 0.5

            foot_access_score = (
                0.5
                + 0.5 * pedestrian_path_coverage
            )

            # -------------------------------------------------
            # REAL OSM LIGHTING
            # -------------------------------------------------

            street_lamp_count = (
                osm_features.get(
                    "street_lamp_count",
                    0,
                )
                or 0
            )

            lit_feature_count = (
                osm_features.get(
                    "lit_feature_count",
                    0,
                )
                or 0
            )

            if road_count > 0:

                lamp_density = min(
                    street_lamp_count / road_count,
                    1.0,
                )

                lit_feature_density = min(
                    lit_feature_count / road_count,
                    1.0,
                )

            else:

                lamp_density = 0.0
                lit_feature_density = 0.0

            if lit_feature_count > 0:

                explicit_lit_score = 1.0

            else:

                explicit_lit_score = 0.5

            # -------------------------------------------------
            # REAL OSM SURFACE
            # -------------------------------------------------

            surface_distribution = osm_features.get(
                "surface_distribution",
                {},
            )

            surface_score = 0.5

            if surface_distribution:

                total_surface = sum(
                    surface_distribution.values()
                )

                good_surfaces = (
                    surface_distribution.get(
                        "paving_stones",
                        0,
                    )
                    + surface_distribution.get(
                        "asphalt",
                        0,
                    )
                    + surface_distribution.get(
                        "concrete",
                        0,
                    )
                    + surface_distribution.get(
                        "paved",
                        0,
                    )
                )

                if total_surface > 0:

                    surface_score = (
                        good_surfaces
                        / total_surface
                    )

            # -------------------------------------------------
            # DERIVED FEATURES
            # -------------------------------------------------

            pedestrian_infrastructure_score = (
                0.45 * road_type_score
                + 0.25 * foot_access_score
                + 0.20 * surface_score
                + 0.10 * width_score
            )

            lighting_score = (
                0.55 * lamp_density
                + 0.30 * lit_feature_density
                + 0.15 * explicit_lit_score
            )

            # -------------------------------------------------
            # ML FEATURES
            # -------------------------------------------------

            ml_features = {

                "road_type_score":
                    road_type_score,

                "foot_access_score":
                    foot_access_score,

                "surface_score":
                    surface_score,

                "width_score":
                    width_score,

                "sidewalk_known":
                    sidewalk_known,

                "sidewalk_positive":
                    sidewalk_positive,

                "explicit_lit_score":
                    explicit_lit_score,

                "crossing_density":
                    crossing_density,

                "lamp_density":
                    lamp_density,

                "lit_feature_density":
                    lit_feature_density,

                "pedestrian_infrastructure_score":
                    pedestrian_infrastructure_score,

                "crossing_score":
                    crossing_density,

                "lighting_score":
                    lighting_score,
            }

            # -------------------------------------------------
            # ML PREDICTION
            # -------------------------------------------------
            print("\n=== ML ROUTE FEATURES ===")
            print(json.dumps(ml_features, indent=2))
            safety_prediction = predict_safety(
                ml_features
            )

            # -------------------------------------------------
            # EXPLAINABILITY
            # -------------------------------------------------

            positive_reasons = []
            caution_reasons = []

            # Surface
            if surface_score >= 0.8:

                positive_reasons.append(
                    "Good mapped road surface conditions"
                )

            elif surface_score < 0.5:

                caution_reasons.append(
                    "Some less suitable surface types are mapped"
                )

            # Lighting
            if street_lamp_count > 0:

                positive_reasons.append(
                    f"{street_lamp_count} mapped street lamp(s)"
                )

            elif lit_feature_count > 0:

                positive_reasons.append(
                    "Mapped lighting information is available"
                )

            else:

                caution_reasons.append(
                    "No mapped street lamps were found"
                )

            # Sidewalk
            if sidewalk_known:

                if sidewalk_positive:

                    positive_reasons.append(
                        "Mapped sidewalk coverage is good"
                    )

                elif sidewalk_score < 0.5:

                    caution_reasons.append(
                        "Limited mapped sidewalk coverage"
                    )

            else:

                caution_reasons.append(
                    "Sidewalk information is unavailable in OSM"
                )

            # Pedestrian infrastructure
            if pedestrian_path_coverage > 0:

                positive_reasons.append(
                    "Dedicated pedestrian infrastructure detected"
                )

            # Crossings
            if crossing_count > 0:

                positive_reasons.append(
                    f"{crossing_count} mapped crossing feature(s)"
                )

            else:

                caution_reasons.append(
                    "No mapped crossings detected along this route"
                )

            # Road type
            if road_type_score >= 0.8:

                positive_reasons.append(
                    "Route uses pedestrian-friendly road types"
                )

            elif road_type_score < 0.5:

                caution_reasons.append(
                    "Route contains less pedestrian-friendly road types"
                )

            # Data availability
            if width is None:

                caution_reasons.append(
                    "Road width information is unavailable"
                )

            # -------------------------------------------------
            # FALLBACK REASONS
            # -------------------------------------------------

            if not positive_reasons:

                positive_reasons.append(
                    "No strong positive OSM indicators were detected"
                )

            if not caution_reasons:

                caution_reasons.append(
                    "No major OSM data limitations detected"
                )


            # -------------------------------------------------
            # ATTACH ML + EXPLANATION DATA
            # -------------------------------------------------

            osm_features["ml_features"] = (
                ml_features
            )

            osm_features["safety_prediction"] = (
                safety_prediction
            )

            osm_features["explanation"] = {
                "positive_reasons": positive_reasons,
                "caution_reasons": caution_reasons,
            }

            osm_status = "ok"

        except OSMError:

            raw_osm = None
            osm_features = None
            osm_status = "unavailable"

        route = {
            "route_id": f"route_{index + 1}",
            "distance_m": summary.get("distance"),
            "duration_s": summary.get("duration"),
            "geometry": geometry,
            "segments": properties.get(
                "segments",
                [],
            ),
            "osm_status": osm_status,
            "osm_features": osm_features,
        }

        if osm_status == "unavailable":

            route["osm_error"] = (
                "OpenStreetMap feature data was temporarily unavailable."
            )

        routes.append(route)

    # =========================================================
    # ROUTE RANKING
    # =========================================================

    available_routes = [
        route
        for route in routes
        if route.get("osm_status") == "ok"
        and route.get("osm_features")
        and route["osm_features"].get("safety_prediction")
    ]

    if available_routes:

        distances = [
            float(route.get("distance_m") or 0)
            for route in available_routes
        ]

        min_distance = min(distances)
        max_distance = max(distances)

        for route in available_routes:

            safety_prediction = (
                route["osm_features"]
                ["safety_prediction"]
            )

            safety_score = float(
                safety_prediction.get(
                    "safety_score",
                    50.0,
                )
            )

            distance = float(
                route.get("distance_m") or 0
            )

            # -------------------------------------------------
            # Distance efficiency
            # -------------------------------------------------

            if max_distance == min_distance:

                distance_efficiency = 1.0

            else:

                distance_efficiency = (
                    max_distance - distance
                ) / (
                    max_distance - min_distance
                )

            distance_score = (
                distance_efficiency * 100
            )

            # -------------------------------------------------
            # Final route score
            # -------------------------------------------------

            final_route_score = (
                0.80 * safety_score
                + 0.20 * distance_score
            )

            route["distance_efficiency"] = round(
                distance_efficiency,
                4,
            )

            route["route_score"] = round(
                final_route_score,
                2,
            )

        # -----------------------------------------------------
        # Sort routes
        # -----------------------------------------------------

        available_routes.sort(
            key=lambda route: route["route_score"],
            reverse=True,
        )

        # -----------------------------------------------------
        # Assign ranks
        # -----------------------------------------------------

        for rank, route in enumerate(
            available_routes,
            start=1,
        ):

            route["rank"] = rank

        # -----------------------------------------------------
        # Unavailable OSM routes go last
        # -----------------------------------------------------

        unavailable_routes = [
            route
            for route in routes
            if route not in available_routes
        ]

        routes = (
            available_routes
            + unavailable_routes
        )

    # =========================================================
    # RECOMMENDED ROUTE
    # =========================================================

    recommended_route = None

    if routes:

        for route in routes:

            if route.get("rank") == 1:

                recommended_route = route
                break

    # =========================================================
    # RECOMMENDATION SUMMARY
    # =========================================================

    recommendation = None

    if recommended_route:

        recommended_osm = (
            recommended_route.get(
                "osm_features"
            )
            or {}
        )

        recommended_prediction = (
            recommended_osm.get(
                "safety_prediction"
            )
            or {}
        )

        recommendation = {
            "title": "Safest recommended route",

            "route_id": recommended_route[
                "route_id"
            ],

            "safety_score": recommended_prediction.get(
                "safety_score"
            ),

            "route_score": recommended_route.get(
                "route_score"
            ),

            "distance_m": recommended_route.get(
                "distance_m"
            ),

            "reason": (
                "This route has the highest overall "
                "route score after considering safety "
                "indicators and distance."
            ),

            "explanation": (
                recommended_osm.get(
                    "explanation",
                    {}
                )
            ),
        }

    # =========================================================
    # FINAL RESPONSE
    # =========================================================

    return {
    "status": "ok",
    "profile": "foot-walking",
    "route_count": len(routes),

    "destination": {
        "requested": {
            "latitude": request.destination.latitude,
            "longitude": request.destination.longitude,
        },
        "resolved": (
            {
                "latitude": destination_latitude,
                "longitude": destination_longitude,
            }
            if destination_adjusted
            else None
        ),
        "adjusted": destination_adjusted,
        "adjustment_reason": (
            "Original destination was not directly routable. "
            "A nearby walkable OSM access point was used."
            if destination_adjusted
            else None
        ),
    },

    "recommended_route_id": (
        recommended_route["route_id"]
        if recommended_route
        else None
    ),

    "recommendation": recommendation,

    "routes": routes,
}