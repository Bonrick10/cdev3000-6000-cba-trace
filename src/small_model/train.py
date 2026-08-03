"""Fit fraud-derived clusters and persist versioned cluster evidence."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, MiniBatchKMeans
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.features import (
    CATEGORICAL_FEATURES,
    MODEL_FEATURES,
    NUMERIC_FEATURES,
    build_historical_features,
    is_model_eligible,
)
from src.features.data import read_historical_transactions
from src.label import Label
from src.settings import RANDOM_SEED
from src.small_model.config import (
    DISTANCE_QUANTILE,
    MAX_CLUSTERS,
    MIN_FRAUDS_PER_CLUSTER,
    MODEL_PATH,
    SMALL_MODEL_WINDOW_DAYS,
)
from src.small_model.statistics import (
    assignment_details,
    calculate_cluster_statistics,
)


def build_preprocessor() -> ColumnTransformer:
    """Create behaviour-only preprocessing shared by fit and assignment."""
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("one_hot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        [
            ("numeric", numeric, NUMERIC_FEATURES),
            ("categorical", categorical, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )


def prepare_population(
    raw_transactions: pd.DataFrame, as_of: Optional[datetime] = None
) -> pd.DataFrame:
    """Build prior-history features, then select the eligible rolling window."""
    features = build_historical_features(raw_transactions)
    eligible = features[is_model_eligible(features)].copy()
    if eligible.empty:
        return eligible.reset_index(drop=True)
    reference_time = pd.Timestamp(as_of or features["transaction_time"].max())
    if reference_time.tzinfo is None:
        reference_time = reference_time.tz_localize("UTC")
    else:
        reference_time = reference_time.tz_convert("UTC")
    cutoff = reference_time - pd.Timedelta(days=SMALL_MODEL_WINDOW_DAYS)
    recent = eligible[
        (eligible["transaction_time"] >= cutoff)
        & (eligible["transaction_time"] <= reference_time)
    ]
    return recent.reset_index(drop=True)


def choose_clusterer(
    transformed_fraud: Any,
) -> Tuple[Any, Optional[float]]:
    """Choose K using silhouette quality and MiniBatch when needed."""
    count = len(transformed_fraud)
    if count < 2:
        raise ValueError("Small-model training requires at least two confirmed frauds.")
    maximum = min(
        MAX_CLUSTERS,
        count - 1,
        max(1, count // MIN_FRAUDS_PER_CLUSTER),
    )
    if maximum < 2:
        model = KMeans(n_clusters=1, n_init=10, random_state=RANDOM_SEED)
        model.fit(transformed_fraud)
        return model, None

    best_model = None
    best_score = float("-inf")
    for clusters in range(2, maximum + 1):
        model_class = MiniBatchKMeans if count >= 50_000 else KMeans
        kwargs = {
            "n_clusters": clusters,
            "n_init": 10,
            "random_state": RANDOM_SEED,
        }
        if model_class is MiniBatchKMeans:
            kwargs["batch_size"] = 2048
        candidate = model_class(**kwargs)
        labels = candidate.fit_predict(transformed_fraud)
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(
            transformed_fraud,
            labels,
            sample_size=min(count, 5_000),
            random_state=RANDOM_SEED,
        )
        if score > best_score:
            best_model, best_score = candidate, float(score)
    if best_model is None:
        raise ValueError("No stable fraud-pattern clustering could be fitted.")
    return best_model, best_score


def fit_small_model(population: pd.DataFrame) -> Dict[str, Any]:
    """Fit preprocessing on confirmed fraud, then profile the eligible population."""
    missing = [name for name in MODEL_FEATURES if name not in population]
    if missing:
        raise ValueError(f"Small-model population is missing features: {missing}")
    fraud = population[
        population["original_label"] == Label.CONFIRMED_FRAUDULENT.value
    ].copy()
    if len(fraud) < 2:
        raise ValueError("Small-model training requires at least two confirmed frauds.")

    preprocessor = build_preprocessor()
    transformed_fraud = preprocessor.fit_transform(fraud[MODEL_FEATURES])
    clusterer, silhouette = choose_clusterer(transformed_fraud)
    fraud_clusters = clusterer.predict(transformed_fraud).astype(int)
    fraud_distances = clusterer.transform(transformed_fraud)
    limits = {}
    for cluster_id in range(clusterer.n_clusters):
        member_distances = fraud_distances[fraud_clusters == cluster_id, cluster_id]
        quantile = float(np.quantile(member_distances, DISTANCE_QUANTILE))
        limits[cluster_id] = max(quantile * 1.25, 1e-6)

    transformed_population = preprocessor.transform(population[MODEL_FEATURES])
    cluster_ids, distances, confidence, accepted = assignment_details(
        transformed_population, clusterer, limits
    )
    statistics = calculate_cluster_statistics(
        population, cluster_ids, accepted, clusterer.n_clusters
    )
    version = datetime.now(timezone.utc).strftime("small-%Y%m%dT%H%M%S%fZ")
    return {
        "preprocessor": preprocessor,
        "clusterer": clusterer,
        "feature_columns": list(MODEL_FEATURES),
        "distance_limits": limits,
        "cluster_statistics": statistics,
        "metadata": {
            "version": version,
            "algorithm": type(clusterer).__name__,
            "number_of_clusters": int(clusterer.n_clusters),
            "confirmed_fraud_training_rows": int(len(fraud)),
            "eligible_population_rows": int(len(population)),
            "silhouette_score": silhouette,
            "mean_membership_confidence": float(np.mean(confidence)),
            "accepted_population_rows": int(accepted.sum()),
            "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        },
    }


def save_bundle(bundle: Dict[str, Any], path: Path = MODEL_PATH) -> None:
    """Atomically persist model-version-specific centroids and statistics."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    joblib.dump(bundle, temporary)
    os.replace(temporary, path)


def load_bundle(path: Path = MODEL_PATH) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Small-model artifact not found at {path}. "
            "Run `python -m src.main train-small`."
        )
    bundle = joblib.load(path)
    if bundle.get("feature_columns") != MODEL_FEATURES:
        raise ValueError(
            "Small-model artifact feature schema does not match this code."
        )
    return bundle


def train_from_database(
    path: Path = MODEL_PATH, db=None, as_of: Optional[datetime] = None
) -> Dict[str, Any]:
    """Train from the current eligible historical population."""
    population = prepare_population(read_historical_transactions(db=db), as_of)
    if population.empty:
        raise ValueError("No model-eligible transactions were found.")
    bundle = fit_small_model(population)
    bundle["metadata"].update(
        {
            "population_window_days": SMALL_MODEL_WINDOW_DAYS,
            "population_start": population["transaction_time"].min().isoformat(),
            "population_end": population["transaction_time"].max().isoformat(),
        }
    )
    save_bundle(bundle, path)
    return bundle
