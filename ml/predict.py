from pathlib import Path

import joblib
import pandas as pd


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "safewalk_training_dataset.csv"
)

MODEL_FILE = (
    PROJECT_ROOT
    / "ml"
    / "models"
    / "safewalk_random_forest.joblib"
)


# These MUST match the features used during training.
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


def load_model():
    if not MODEL_FILE.exists():
        raise FileNotFoundError(
            f"Model not found: {MODEL_FILE}"
        )

    return joblib.load(MODEL_FILE)


def predict_dataframe(df):
    """
    Predict safety class for one or more feature rows.

    Returns a copy of the dataframe with:
        predicted_safety_class
        prediction_probability
    """

    model = load_model()

    missing = [
        feature
        for feature in FEATURES
        if feature not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required features: {missing}"
        )

    X = df[FEATURES].copy()

    predictions = model.predict(X)

    probabilities = model.predict_proba(X).max(axis=1)

    result = df.copy()

    result["predicted_safety_class"] = predictions
    result["prediction_probability"] = probabilities

    return result


def main():

    print("Loading trained model...")

    model = load_model()

    print(f"Model loaded: {MODEL_FILE}")

    print("\nLoading training dataset...")

    df = pd.read_csv(DATA_FILE)

    # Test several different rows rather than only one.
    sample = df.sample(
        n=10,
        random_state=42,
    ).copy()

    result = predict_dataframe(sample)

    print("\nPrediction results:")

    output_columns = [
        "osm_id",
        "pseudo_safety_score",
        "safety_label",
        "predicted_safety_class",
        "prediction_probability",
    ]

    print(
        result[output_columns]
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()