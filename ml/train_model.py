from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "safewalk_training_dataset.csv"
)

MODEL_DIR = PROJECT_ROOT / "ml" / "models"
MODEL_FILE = MODEL_DIR / "safewalk_random_forest.joblib"


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

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

TARGET = "safety_label"


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Training dataset not found: {DATA_FILE}"
        )

    print("Loading training dataset...")

    df = pd.read_csv(DATA_FILE)

    print(f"Rows: {len(df):,}")
    print(f"Features: {len(FEATURES)}")

    # -----------------------------------------------------
    # Prepare X and y
    # -----------------------------------------------------

    X = df[FEATURES].copy()
    y = df[TARGET].copy()

    print("\nFeatures used:")
    for feature in FEATURES:
        print(f"  - {feature}")

    print("\nTarget distribution:")
    print(y.value_counts())

    # -----------------------------------------------------
    # Train / validation / test split
    #
    # 70% train
    # 15% validation
    # 15% test
    # -----------------------------------------------------

    X_train, X_temp, y_train, y_temp = train_test_split(
        X,
        y,
        test_size=0.30,
        random_state=42,
        stratify=y,
    )

    X_val, X_test, y_val, y_test = train_test_split(
        X_temp,
        y_temp,
        test_size=0.50,
        random_state=42,
        stratify=y_temp,
    )

    print("\nDataset split:")
    print(f"  Training:   {len(X_train):,}")
    print(f"  Validation: {len(X_val):,}")
    print(f"  Testing:    {len(X_test):,}")

    # -----------------------------------------------------
    # Random Forest
    # -----------------------------------------------------

    print("\nTraining Random Forest...")

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_train, y_train)

    print("Training complete.")

    # -----------------------------------------------------
    # Validation
    # -----------------------------------------------------

    print("\nValidation results:")

    val_predictions = model.predict(X_val)

    val_accuracy = accuracy_score(
        y_val,
        val_predictions,
    )

    print(
        f"Validation accuracy: "
        f"{val_accuracy:.4f}"
    )

    print("\nValidation classification report:")
    print(
        classification_report(
            y_val,
            val_predictions,
            digits=4,
        )
    )

    # -----------------------------------------------------
    # Final test evaluation
    # -----------------------------------------------------

    print("\nTest results:")

    test_predictions = model.predict(X_test)

    test_accuracy = accuracy_score(
        y_test,
        test_predictions,
    )

    print(
        f"Test accuracy: "
        f"{test_accuracy:.4f}"
    )

    print("\nTest classification report:")

    print(
        classification_report(
            y_test,
            test_predictions,
            digits=4,
        )
    )

    # -----------------------------------------------------
    # Confusion matrix
    # -----------------------------------------------------

    print("\nConfusion matrix:")

    labels = sorted(y.unique())

    cm = confusion_matrix(
        y_test,
        test_predictions,
        labels=labels,
    )

    print(
        pd.DataFrame(
            cm,
            index=[
                f"Actual {label}"
                for label in labels
            ],
            columns=[
                f"Predicted {label}"
                for label in labels
            ],
        )
    )

    # -----------------------------------------------------
    # Feature importance
    # -----------------------------------------------------

    print("\nFeature importance:")

    importance = pd.Series(
        model.feature_importances_,
        index=FEATURES,
    ).sort_values(ascending=False)

    print(importance.to_string())

    # -----------------------------------------------------
    # Save model
    # -----------------------------------------------------

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        model,
        MODEL_FILE,
    )

    print("\nModel saved:")
    print(MODEL_FILE)


if __name__ == "__main__":
    main()