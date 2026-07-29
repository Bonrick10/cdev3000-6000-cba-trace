"""SQL-backed historical data reads for model training and refresh."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from src.utils.db import NeonDB

SQL_DIRECTORY = Path(__file__).resolve().parent / "sql"


def read_historical_transactions(
    end_time: Optional[datetime] = None, db: Optional[NeonDB] = None
) -> pd.DataFrame:
    """Read transaction attempts before an exclusive timestamp."""
    database = db or NeonDB()
    rows = database.query_sql_file(
        SQL_DIRECTORY / "get_historical_transactions.sql",
        {"end_time": end_time or datetime.now(timezone.utc)},
    )
    return pd.DataFrame(rows)
