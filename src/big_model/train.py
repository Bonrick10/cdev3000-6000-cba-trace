"""Build, train, save and load the binary big fraud model."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    OneHotEncoder,
    StandardScaler,
)

from .handle_data import (
    CATEGORICAL_FEATURES,
    MODEL_FEATURES,
    NUMERIC_FEATURES,
)


MODEL_DIRECTORY = (
    Path(__file__).resolve().parent
    / "models"
)

CURRENT_MODEL_PATH = (
    MODEL_DIRECTORY
    / "big_model_current.joblib"
)


def build_model() -> Pipeline:
    """Build the preprocessing and model pipeline."""

    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                ),
            ),
            (
                "scaler",
                StandardScaler(),
            ),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="most_frequent"
                ),
            ),
            (
                "one_hot",
                OneHotEncoder(
                    handle_unknown="ignore",
                    min_frequency=2,
                ),
            ),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                numeric_pipeline,
                NUMERIC_FEATURES,
            ),
            (
                "categorical",
                categorical_pipeline,
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="drop",
    )

    classifier = LogisticRegression(
        class_weight="balanced",
        max_iter=2_000,
        solver="lbfgs",
        random_state=42,
    )

    return Pipeline(
        steps=[
            (
                "preprocessor",
                preprocessor,
            ),
            (
                "classifier",
                classifier,
            ),
        ]
    )


def train_model(
    training_data: pd.DataFrame,
) -> Pipeline:
    """Train on mature binary targets."""

    required_columns = (
        MODEL_FEATURES
        + ["target"]
    )

    missing_columns = [
        column
        for column
        in required_columns
        if column
        not in training_data.columns
    ]

    if missing_columns:
        raise ValueError(
            "Training data is missing: "
            f"{missing_columns}"
        )

    if (
        training_data[
            "target"
        ].nunique()
        != 2
    ):
        raise ValueError(
            "Training requires both mature "
            "non-fraud and fraud classes."
        )

    X_train = training_data[
        MODEL_FEATURES
    ]

    y_train = training_data[
        "target"
    ]

    model = build_model()

    model.fit(
        X_train,
        y_train,
    )

    return model


def save_model_bundle(
    model: Pipeline,
    metadata: dict[str, Any],
    path: Path = CURRENT_MODEL_PATH,
) -> None:
    """Persist preprocessing, model and metadata."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    bundle = {
        "model":
            model,

        "feature_columns":
            MODEL_FEATURES,

        "metadata": {
            **metadata,

            "saved_at_utc":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "model_type":
                "binary_logistic_regression",

            "positive_class":
                "mature_fraud_or_high_risk",

            "version":
                "big-model-v3",
        },
    }

    joblib.dump(
        bundle,
        path,
    )


def load_model_bundle(
    path: Path = CURRENT_MODEL_PATH,
) -> dict[str, Any]:
    """Load the persisted model bundle."""

    if not path.exists():
        raise FileNotFoundError(
            "No trained model exists at "
            f"{path}. Run:\n"
            "python -m big_model.main train"
        )

    return joblib.load(path)