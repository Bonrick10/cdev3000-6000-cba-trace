"""Build, train and save the multinomial logistic regression model."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from Handle_data import MODEL_FEATURES


MODEL_DIRECTORY = Path("models")
CURRENT_MODEL_PATH = MODEL_DIRECTORY / "big_model_current.joblib"


def build_model() -> Pipeline:
    """
    Build the model pipeline.

    Scaling is needed because logistic regression is affected by
    differences in feature magnitude.
    """

    return Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="median"),
            ),
            (
                "scaler",
                StandardScaler(),
            ),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=2_000,
                    solver="lbfgs",
                    random_state=42,
                ),
            ),
        ]
    )


def train_model(
    training_data: pd.DataFrame,
) -> Pipeline:
    """Train the big model on model-ready transaction features."""

    missing_features = [
        column
        for column in MODEL_FEATURES
        if column not in training_data.columns
    ]

    if missing_features:
        raise ValueError(
            f"Training data is missing: {missing_features}"
        )

    if training_data["model_label"].nunique() < 2:
        raise ValueError(
            "Training data must contain at least two label classes."
        )

    X_train = training_data[MODEL_FEATURES]
    y_train = training_data["model_label"]

    model = build_model()
    model.fit(X_train, y_train)

    return model


def save_model_bundle(
    model: Pipeline,
    metadata: dict[str, Any],
    path: Path = CURRENT_MODEL_PATH,
) -> None:
    """Save the model, features and training metadata."""

    MODEL_DIRECTORY.mkdir(parents=True, exist_ok=True)

    bundle = {
        "model": model,
        "feature_columns": MODEL_FEATURES,
        "metadata": metadata,
    }

    joblib.dump(bundle, path)


def load_model_bundle(
    path: Path = CURRENT_MODEL_PATH,
) -> dict[str, Any]:
    """Load a previously saved model bundle."""

    if not path.exists():
        raise FileNotFoundError(
            f"No trained model exists at {path}."
        )

    return joblib.load(path)