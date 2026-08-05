"""Small-model rebuild after observable customer fraud feedback."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.small_model.config import MODEL_PATH
from src.small_model.train import train_from_database


def rebuild_from_database(
    path: Path = MODEL_PATH, db=None, as_of: Optional[datetime] = None
) -> Dict[str, Any]:
    """Fully rebuild clusters and statistics from the current rolling window."""
    return train_from_database(path=path, db=db, as_of=as_of)


# Backward-compatible name for callers from earlier repository versions. A
# "refresh" now deliberately performs a complete rebuild and creates a new
# model version.
refresh_statistics_from_database = rebuild_from_database
