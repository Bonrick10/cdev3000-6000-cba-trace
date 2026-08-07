"""Train and persist the supervised fraud-risk model."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.big_model.config import MATURE_LABEL_MAPPING, MODEL_PATH
from src.big_model.evaluate import evaluate_model
from src.features import (
    CATEGORICAL_FEATURES,
    MODEL_FEATURES,
    NUMERIC_FEATURES,
    build_historical_features,
    is_model_eligible,
)
from src.features.data import read_historical_transactions
from src.settings import RANDOM_SEED


def maturity_cutoff(as_of: Optional[datetime] = None) -> pd.Timestamp:
    """Return the exclusive cutoff for the agreed two-month outcome period."""
    current = pd.Timestamp(as_of or datetime.now(timezone.utc))
    if current.tzinfo is None:
        current = current.tz_localize("UTC")
    else:
        current = current.tz_convert("UTC")
    return current - pd.DateOffset(months=2)


def training_reference_time(
    raw_transactions: pd.DataFrame, as_of: Optional[datetime] = None
) -> pd.Timestamp:
    """Anchor static snapshots to their latest transaction, not wall-clock time."""
    if as_of is not None:
        reference = pd.Timestamp(as_of)
    elif raw_transactions.empty:
        raise ValueError("Cannot infer a training reference time from empty data.")
    else:
        reference = pd.to_datetime(raw_transactions["transaction_time"], utc=True).max()
    if reference.tzinfo is None:
        return reference.tz_localize("UTC")
    return reference.tz_convert("UTC")


def build_model() -> Pipeline:
    """Create reusable preprocessing and logistic regression."""
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "one_hot",
                OneHotEncoder(handle_unknown="ignore", min_frequency=2),
            ),
        ]
    )
    preprocessing = ColumnTransformer(
        [
            ("numeric", numeric, NUMERIC_FEATURES),
            ("categorical", categorical, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )
    return Pipeline(
        [
            ("preprocessing", preprocessing),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=2_000,
                    solver="lbfgs",
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )


def prepare_training_data(raw_transactions: pd.DataFrame) -> pd.DataFrame:
    """Build features, retain model-routed rows, and map targets in memory."""
    features = build_historical_features(raw_transactions)
    eligible = features[is_model_eligible(features)].copy()
    eligible["target"] = eligible["original_label"].map(MATURE_LABEL_MAPPING)
    eligible = eligible.dropna(subset=["target"]).copy()
    eligible["target"] = eligible["target"].astype(int)
    return eligible.reset_index(drop=True)


def chronological_split(
    dataframe: pd.DataFrame, train_fraction: float = 0.8
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be between zero and one.")
    ordered = dataframe.sort_values(["transaction_time", "transaction_id"])
    index = int(len(ordered) * train_fraction)
    while index < len(ordered) and ordered.iloc[:index]["target"].nunique() < 2:
        index += 1
    if index <= 0 or index >= len(ordered):
        raise ValueError(
            "A chronological training split containing both targets could not "
            "leave any evaluation rows."
        )
    return ordered.iloc[:index].copy(), ordered.iloc[index:].copy()


def fit_model(training_data: pd.DataFrame) -> Pipeline:
    """Fit a fresh model after validating feature and target classes."""
    missing = [
        name for name in MODEL_FEATURES + ["target"] if name not in training_data
    ]
    if missing:
        raise ValueError(f"Big-model training data is missing columns: {missing}")
    if training_data["target"].nunique() != 2:
        raise ValueError(
            "Big-model training requires both fraud and non-fraud targets."
        )
    model = build_model()
    model.fit(training_data[MODEL_FEATURES], training_data["target"])
    return model


def save_bundle(
    model: Pipeline,
    metadata: Dict[str, Any],
    path: Path = MODEL_PATH,
) -> Dict[str, Any]:
    """Atomically persist preprocessing, classifier, and metadata."""
    path.parent.mkdir(parents=True, exist_ok=True)
    version = metadata.get(
        "version", datetime.now(timezone.utc).strftime("big-%Y%m%dT%H%M%S%fZ")
    )
    bundle = {
        "model": model,
        "feature_columns": list(MODEL_FEATURES),
        "metadata": {
            **metadata,
            "version": version,
            "model_type": "logistic_regression",
            "saved_at_utc": datetime.now(timezone.utc).isoformat(),
        },
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    joblib.dump(bundle, temporary)
    os.replace(temporary, path)
    return bundle


def load_bundle(path: Path = MODEL_PATH) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Big-model artifact not found at {path}. "
            "Run `python -m src.main train-big`."
        )
    bundle = joblib.load(path)
    if bundle.get("feature_columns") != MODEL_FEATURES:
        raise ValueError("Big-model artifact feature schema does not match this code.")
    return bundle


def train_from_database(
    as_of: Optional[datetime] = None,
    path: Path = MODEL_PATH,
    db=None,
) -> Dict[str, Any]:
    """Evaluate chronologically, refit on all mature rows, and save."""
    raw = read_historical_transactions(db=db)
    reference_time = training_reference_time(raw, as_of)
    cutoff = maturity_cutoff(reference_time.to_pydatetime())
    transaction_times = pd.to_datetime(raw["transaction_time"], utc=True)
    mature_raw = raw[transaction_times < cutoff].copy()
    model_data = prepare_training_data(mature_raw)
    if model_data.empty:
        raise ValueError("No mature model-eligible transactions were found.")
    train_data, test_data = chronological_split(model_data)
    candidate = fit_model(train_data)
    metrics = evaluate_model(candidate, test_data)
    final_model = fit_model(model_data)
    return save_bundle(
        final_model,
        {
            "maturity_cutoff": cutoff.isoformat(),
            "training_as_of": reference_time.isoformat(),
            "training_rows": int(len(model_data)),
            "target_counts": {
                str(key): int(value)
                for key, value in model_data["target"].value_counts().items()
            },
            "chronological_test_metrics": metrics,
            "mature_label_mapping": dict(MATURE_LABEL_MAPPING),
        },
        path,
    )
