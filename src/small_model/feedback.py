"""Idempotent cluster-statistics refresh after customer feedback."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.features import MODEL_FEATURES
from src.features.data import read_historical_transactions
from src.small_model.config import MODEL_PATH
from src.small_model.statistics import (
    assignment_details,
    calculate_cluster_statistics,
)
from src.small_model.train import (
    load_bundle,
    prepare_population,
    save_bundle,
)


def refresh_statistics_from_database(
    path: Path = MODEL_PATH, db=None, as_of: Optional[datetime] = None
) -> Dict[str, Any]:
    """Recompute statistics from source data rather than incrementing counters."""
    bundle = load_bundle(path)
    population = prepare_population(read_historical_transactions(db=db), as_of)
    if population.empty:
        raise ValueError(
            "No model-eligible transactions remain for statistics refresh."
        )
    transformed = bundle["preprocessor"].transform(population[MODEL_FEATURES])
    clusters, _, _, accepted = assignment_details(
        transformed, bundle["clusterer"], bundle["distance_limits"]
    )
    bundle["cluster_statistics"] = calculate_cluster_statistics(
        population,
        clusters,
        accepted,
        int(bundle["metadata"]["number_of_clusters"]),
    )
    bundle["metadata"].update(
        {
            "statistics_population_rows": int(len(population)),
            "statistics_population_start": population[
                "transaction_time"
            ].min().isoformat(),
            "statistics_population_end": population[
                "transaction_time"
            ].max().isoformat(),
            "statistics_refreshed_at_utc": datetime.now(timezone.utc).isoformat(),
        }
    )
    save_bundle(bundle, path)
    return bundle
