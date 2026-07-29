"""Database read for rules and live behavioural feature context."""

from pathlib import Path
from typing import Any, Dict, Optional

from src.settings import (
    RECURRING_TRANSACTION_AGE_DAYS,
    RECURRING_TRANSACTION_AMOUNT_VARIANCE,
    RECURRING_TRANSACTION_TIME_VARIANCE_MINUTES,
)
from src.utils.db import NeonDB

SQL_PATH = Path(__file__).resolve().parent / "sql" / "get_surrounding_info.sql"


def read_context(
    transaction: Dict[str, Any], db: Optional[NeonDB] = None
) -> Dict[str, Any]:
    """Return strictly prior context for a pending transaction."""
    database = db or NeonDB()
    params = dict(transaction)
    params.update(
        {
            "recurring_age_days": RECURRING_TRANSACTION_AGE_DAYS,
            "recurring_amount_variance": RECURRING_TRANSACTION_AMOUNT_VARIANCE,
            "recurring_time_variance_minutes": (
                RECURRING_TRANSACTION_TIME_VARIANCE_MINUTES
            ),
        }
    )
    rows = database.query_sql_file(SQL_PATH, params)
    if not rows:
        raise ValueError(
            "Sender account was not found or no historical context could be generated."
        )
    return dict(rows[0])
