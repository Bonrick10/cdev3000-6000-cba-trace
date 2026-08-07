"""SQL-backed historical data reads for model training and refresh."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from src.settings import MODEL_DATA_SOURCE
from src.utils.db import NeonDB

SQL_DIRECTORY = Path(__file__).resolve().parent / "sql"
SOURCE_QUERIES = {
    "full_txns": SQL_DIRECTORY / "get_historical_transactions.sql",
    "transactions": SQL_DIRECTORY / "get_live_historical_transactions.sql",
}


def read_historical_transactions(
    end_time: Optional[datetime] = None,
    db: Optional[NeonDB] = None,
    source: Optional[str] = None,
) -> pd.DataFrame:
    """Read a whitelisted development snapshot or live transaction history."""
    selected_source = (source or MODEL_DATA_SOURCE).strip().lower()
    try:
        query_path = SOURCE_QUERIES[selected_source]
    except KeyError as error:
        supported = ", ".join(sorted(SOURCE_QUERIES))
        raise ValueError(
            f"Unsupported MODEL_DATA_SOURCE {selected_source!r}; choose {supported}."
        ) from error
    database = db or NeonDB()
    rows = database.query_sql_file(
        query_path,
        {"end_time": end_time or datetime.now(timezone.utc)},
    )
    return pd.DataFrame(rows)
