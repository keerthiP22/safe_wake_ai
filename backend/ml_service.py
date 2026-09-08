from pathlib import Path

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODEL_FILE = (
    PROJECT_ROOT
    / "ml"
    / "models"
    / "safewalk_random_forest.joblib"
)


FEATURES = [
    "road_type_score",
    "foot_access_score",
    "surface_score",
    "width_score",
    "sidewalk_known",
    "sidewalk_positive",
    "explicit_lit_score",
    "crossing_density",
    "lamp_density",
    "lit_feature_density",
    "pedestrian_infrastructure_score",
    "crossing_score",
    "lighting_score",
]


MODEL = joblib.load(MODEL_FILE)


def predict_safety(features: dict) -> dict:

    row = pd.DataFrame(
        [[
            features.get(feature, 0.5)
            for feature in FEATURES
        ]],
        columns=FEATURES,
    )

    prediction = MODEL.predict(row)[0]

    probabilities = MODEL.predict_proba(row)[0]

    classes = MODEL.classes_

    probability_map = {
        str(cls): float(probability)
        for cls, probability in zip(
            classes,
            probabilities,
        )
    }

    # ---------------------------------------------------------
    # Model-derived suitability score
    # ---------------------------------------------------------
    #
    # This is NOT accident probability.
    #
    # It represents relative pedestrian-infrastructure
    # suitability based on the model's class probabilities.
    #
    # low    -> 0
    # medium -> 50
    # high   -> 100
    # ---------------------------------------------------------

    safety_score = (
        probability_map.get("low", 0.0) * 0
        + probability_map.get("medium", 0.0) * 50
        + probability_map.get("high", 0.0) * 100
    )

    return {
        "safety_score": round(
            float(safety_score),
            2,
        ),

        "safety_class": str(
            prediction
        ),

        "confidence": round(
            float(max(probabilities)),
            4,
        ),

        "probabilities": probability_map,
    }