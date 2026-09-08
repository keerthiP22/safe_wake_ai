"""
SafeWalk AI - Build pseudo-labeled ML dataset
from real Bengaluru OSM data.

The labels generated here are PSEUDO-LABELS representing
pedestrian infrastructure suitability.

They are NOT accident-risk ground truth.
"""

from pathlib import Path
import json
import math
import re

import numpy as np
import pandas as pd

from shapely.geometry import shape, Point
from shapely.strtree import STRtree


# =========================================================
# Paths
# =========================================================

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

ROADS_FILE = DATA / "cleaned_bengaluru_pedestrian_roads.csv"
CROSSINGS_FILE = DATA / "cleaned_bengaluru_crossings.csv"
LIT_FILE = DATA / "cleaned_bengaluru_lit_features.csv"
LAMPS_FILE = DATA / "cleaned_bengaluru_street_lamps.csv"

OUTPUT_FILE = DATA / "safewalk_training_dataset.csv"


# =========================================================
# Configuration
# =========================================================

# Approximate spatial matching radius.
# 0.0015 degrees is roughly 150-165 metres around Bengaluru.
MATCH_RADIUS_DEG = 0.0015


# =========================================================
# Geometry helpers
# =========================================================

def parse_geometry(value):
    """Parse a GeoJSON geometry string safely."""

    if pd.isna(value):
        return None

    try:
        obj = json.loads(value) if isinstance(value, str) else value
        return shape(obj)

    except Exception:
        return None


def point_from_row(row):
    """Create a Shapely Point from longitude/latitude."""

    try:
        lon = float(row["longitude"])
        lat = float(row["latitude"])

        if math.isfinite(lon) and math.isfinite(lat):
            return Point(lon, lat)

    except (ValueError, TypeError, KeyError):
        pass

    return None


# =========================================================
# Spatial matching
# =========================================================

def associate_points_to_roads(roads, points_df, label):
    """
    Associate point infrastructure features with the
    nearest road geometry.

    Returns:
        counts per road
        list of matched distances
    """

    geometries = roads["_geometry"].tolist()

    valid_geometries = [
        g for g in geometries
        if g is not None
    ]

    if not valid_geometries or points_df.empty:

        return (
            pd.Series(
                0,
                index=roads.index,
                dtype=int,
            ),
            [],
        )

    tree = STRtree(valid_geometries)

    counts = pd.Series(
        0,
        index=roads.index,
        dtype=int,
    )

    distances = []

    # Map geometry identity back to road index.
    geometry_to_road_index = {}

    for idx, geom in zip(
        roads.index,
        roads["_geometry"],
    ):

        if geom is not None:
            geometry_to_road_index[id(geom)] = idx

    for _, row in points_df.iterrows():

        point = point_from_row(row)

        if point is None:
            continue

        try:

            nearest_result = tree.query_nearest(
                point,
                return_distance=True,
            )

            candidate_indices = nearest_result[0]
            candidate_distances = nearest_result[1]

            if len(candidate_indices) == 0:
                continue

            best_pos = int(
                np.argmin(candidate_distances)
            )

            geom_pos = int(
                candidate_indices[best_pos]
            )

            distance = float(
                candidate_distances[best_pos]
            )

            if distance <= MATCH_RADIUS_DEG:

                geom = valid_geometries[geom_pos]

                road_idx = geometry_to_road_index.get(
                    id(geom)
                )

                if road_idx is not None:

                    counts.loc[road_idx] += 1

                    distances.append(distance)

        except Exception:
            continue

    print(
        f"  {label}: matched "
        f"{int(counts.sum())} point features"
    )

    return counts, distances


# =========================================================
# Feature encoding
# =========================================================

def encode_road_type(value):
    """
    Infrastructure suitability contribution from road type.
    """

    if pd.isna(value):
        return 0.0

    mapping = {
        "pedestrian": 1.00,
        "footway": 0.90,
        "path": 0.75,
        "living_street": 0.65,
        "residential": 0.60,
        "service": 0.50,
        "tertiary": 0.50,
        "secondary": 0.45,
        "primary": 0.35,
        "major": 0.30,
    }

    return mapping.get(
        str(value).strip().lower(),
        0.50,
    )


def encode_surface(value):
    """
    Surface suitability contribution.

    Unknown remains neutral.
    """

    if pd.isna(value):
        return 0.50

    value = str(value).strip().lower()

    good = {
        "paving_stones",
        "asphalt",
        "concrete",
        "paved",
        "concrete:plates",
        "tiles",
        "sett",
    }

    poor = {
        "dirt",
        "earth",
        "sand",
        "ground",
        "gravel",
        "fine_gravel",
        "unpaved",
    }

    if value in good:
        return 1.00

    if value in poor:
        return 0.35

    return 0.65


def encode_foot_access(value):
    """
    Foot-access suitability.

    Unknown remains neutral.
    """

    if pd.isna(value):
        return 0.50

    value = str(value).strip().lower()

    mapping = {
        "yes": 1.00,
        "designated": 1.00,
        "permissive": 0.85,
        "customers": 0.55,
        "permit": 0.45,
        "private": 0.25,
    }

    return mapping.get(
        value,
        0.50,
    )


def encode_explicit_lit(value):
    """
    Explicit OSM lighting tag.

    Unknown remains neutral.
    """

    if pd.isna(value):
        return 0.50

    value = str(value).strip().lower()

    if value == "yes":
        return 1.00

    if value == "limited":
        return 0.65

    if value == "no":
        return 0.20

    return 0.50


def width_score(value):
    """
    Score known road/path widths.

    Unknown remains neutral.
    """

    if pd.isna(value):
        return 0.50

    text = str(value).strip().lower()

    numbers = re.findall(
        r"\d+(?:\.\d+)?",
        text,
    )

    if not numbers:
        return 0.50

    try:
        width = float(numbers[0])

    except ValueError:
        return 0.50

    if width >= 3:
        return 1.00

    if width >= 2:
        return 0.85

    if width >= 1:
        return 0.65

    return 0.35


# =========================================================
# Density
# =========================================================

def normalize_density(
    count_series,
    road_count_series,
):
    """
    Calculate infrastructure density consistently
    with the route-level backend.

    density = infrastructure_count / road_count

    The result is capped at 1.0.
    """

    counts = pd.to_numeric(
        count_series,
        errors="coerce",
    ).fillna(0).clip(lower=0)

    road_counts = pd.to_numeric(
        road_count_series,
        errors="coerce",
    ).fillna(0).clip(lower=0)

    density = np.where(
        road_counts > 0,
        counts / road_counts,
        0.0,
    )

    return pd.Series(
        np.minimum(
            density,
            1.0,
        ),
        index=count_series.index,
    )


# =========================================================
# Main dataset construction
# =========================================================

def main():

    print(
        "Loading real Bengaluru OSM datasets..."
    )

    # -----------------------------------------------------
    # Validate input files
    # -----------------------------------------------------

    for path in [
        ROADS_FILE,
        CROSSINGS_FILE,
        LIT_FILE,
        LAMPS_FILE,
    ]:

        if not path.exists():
            raise FileNotFoundError(
                f"Missing input file: {path}"
            )

    # -----------------------------------------------------
    # Load datasets
    # -----------------------------------------------------

    roads = pd.read_csv(
        ROADS_FILE
    )

    crossings = pd.read_csv(
        CROSSINGS_FILE
    )

    lit = pd.read_csv(
        LIT_FILE
    )

    lamps = pd.read_csv(
        LAMPS_FILE
    )

    print(
        f"Roads:     {len(roads):,}"
    )

    print(
        f"Crossings: {len(crossings):,}"
    )

    print(
        f"Lit:       {len(lit):,}"
    )

    print(
        f"Lamps:     {len(lamps):,}"
    )

    # -----------------------------------------------------
    # Parse road geometries
    # -----------------------------------------------------

    print(
        "\nParsing road geometries..."
    )

    roads["_geometry"] = (
        roads["geometry"]
        .apply(parse_geometry)
    )

    valid = roads["_geometry"].notna().sum()

    print(
        f"Valid road geometries: "
        f"{valid:,}/{len(roads):,}"
    )

    # -----------------------------------------------------
    # Spatial infrastructure matching
    # -----------------------------------------------------

    print(
        "\nSpatially associating infrastructure..."
    )

    crossing_count, _ = associate_points_to_roads(
        roads,
        crossings,
        "crossings",
    )

    lamp_count, _ = associate_points_to_roads(
        roads,
        lamps,
        "street lamps",
    )

    # -----------------------------------------------------
    # Lit features
    # -----------------------------------------------------

    print(
        "Processing lit feature geometries..."
    )

    lit_points = []

    for value in lit["geometry"]:

        geom = parse_geometry(value)

        if geom is not None:

            try:

                point = geom.representative_point()

                lit_points.append(
                    {
                        "longitude": point.x,
                        "latitude": point.y,
                    }
                )

            except Exception:
                pass

    lit_points_df = pd.DataFrame(
        lit_points
    )

    lit_count, _ = associate_points_to_roads(
        roads,
        lit_points_df,
        "lit features",
    )

    # -----------------------------------------------------
    # Create result dataframe
    # -----------------------------------------------------

    result = roads.drop(
        columns=["_geometry"]
    ).copy()

    # Infrastructure counts.

    result["crossing_count"] = (
        crossing_count.values
    )

    result["street_lamp_count"] = (
        lamp_count.values
    )

    result["lit_feature_count"] = (
        lit_count.values
    )

    # -----------------------------------------------------
    # Route-compatible density features
    # -----------------------------------------------------

    # Every dataset row represents one road/path
    # infrastructure feature.

    road_count = pd.Series(
        1.0,
        index=result.index,
    )

    result["crossing_density"] = (
        normalize_density(
            result["crossing_count"],
            road_count,
        )
    )

    result["lamp_density"] = (
        normalize_density(
            result["street_lamp_count"],
            road_count,
        )
    )

    result["lit_feature_density"] = (
        normalize_density(
            result["lit_feature_count"],
            road_count,
        )
    )

    # -----------------------------------------------------
    # Basic encoded features
    # -----------------------------------------------------

    result["road_type_score"] = (
        result["road_type"]
        .apply(encode_road_type)
    )

    result["surface_score"] = (
        result["surface"]
        .apply(encode_surface)
    )

    result["foot_access_score"] = (
        result["foot_access"]
        .apply(encode_foot_access)
    )

    result["explicit_lit_score"] = (
        result["lit"]
        .apply(encode_explicit_lit)
    )

    result["width_score"] = (
        result["width"]
        .apply(width_score)
    )

    # -----------------------------------------------------
    # Sidewalk features
    # -----------------------------------------------------

    result["sidewalk_known"] = (
        result["sidewalk"]
        .notna()
        .astype(int)
    )

    result["sidewalk_positive"] = (
        result["sidewalk"]
        .fillna("")
        .astype(str)
        .str.lower()
        .isin(
            [
                "both",
                "separate",
                "raised",
            ]
        )
        .astype(int)
    )

    # -----------------------------------------------------
    # Pedestrian infrastructure score
    # -----------------------------------------------------

    result["pedestrian_infrastructure_score"] = (
        0.45
        * result["road_type_score"]
        + 0.25
        * result["foot_access_score"]
        + 0.20
        * result["surface_score"]
        + 0.10
        * result["width_score"]
    )

    # -----------------------------------------------------
    # Crossing score
    # -----------------------------------------------------

    result["crossing_score"] = (
        result["crossing_density"]
    )

    # -----------------------------------------------------
    # Lighting score
    # -----------------------------------------------------

    result["lighting_score"] = (
        0.55
        * result["lamp_density"]
        + 0.30
        * result["lit_feature_density"]
        + 0.15
        * result["explicit_lit_score"]
    )

    # -----------------------------------------------------
    # Pseudo safety score
    # -----------------------------------------------------

    result["pseudo_safety_score"] = (
        100
        * (
            0.50
            * result[
                "pedestrian_infrastructure_score"
            ]
            + 0.25
            * result["crossing_score"]
            + 0.25
            * result["lighting_score"]
        )
    ).clip(
        0,
        100,
    )

    # -----------------------------------------------------
    # Three-class pseudo labels
    # -----------------------------------------------------

    q33 = result[
        "pseudo_safety_score"
    ].quantile(0.33)

    q67 = result[
        "pseudo_safety_score"
    ].quantile(0.67)

    result["safety_label"] = pd.cut(
        result["pseudo_safety_score"],
        bins=[
            -1,
            q33,
            q67,
            100,
        ],
        labels=[
            "low",
            "medium",
            "high",
        ],
    ).astype(str)

    # -----------------------------------------------------
    # Select output columns
    # -----------------------------------------------------

    feature_columns = [

        "osm_id",

        "road_type",
        "foot_access",
        "surface",
        "width",
        "lit",
        "sidewalk",

        "crossing_count",
        "street_lamp_count",
        "lit_feature_count",

        "crossing_density",
        "lamp_density",
        "lit_feature_density",

        "road_type_score",
        "surface_score",
        "foot_access_score",
        "explicit_lit_score",
        "width_score",

        "sidewalk_known",
        "sidewalk_positive",

        "pedestrian_infrastructure_score",
        "crossing_score",
        "lighting_score",

        "pseudo_safety_score",
        "safety_label",
    ]

    result = result[
        feature_columns
    ]

    # -----------------------------------------------------
    # Save dataset
    # -----------------------------------------------------

    result.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    print(
        "\nDataset created successfully."
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )

    print(
        f"Rows:   {len(result):,}"
    )

    print(
        "\nLabel distribution:"
    )

    print(
        result[
            "safety_label"
        ].value_counts()
    )

    print(
        "\nScore statistics:"
    )

    print(
        result[
            "pseudo_safety_score"
        ]
        .describe()
        .round(2)
    )

    print(
        "\nFirst 5 rows:"
    )

    print(
        result.head()
        .to_string(
            index=False
        )
    )


# =========================================================
# Entry point
# =========================================================

if __name__ == "__main__":
    main()