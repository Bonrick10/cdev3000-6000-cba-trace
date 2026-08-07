"""Data Population Module"""

from pathlib import Path

from src.utils.db import NeonDB

BASE_DIR = Path(__file__).resolve().parent
SQL_DIR = BASE_DIR / "sql"


def populate_data():
    """
    Populates the database with synthetic data.
    """
    db = NeonDB()
    db.execute(db.read_sql_file(SQL_DIR / "clear_tables.sql"))
    db.execute(db.read_sql_file(SQL_DIR / "synthetic_population.sql"))
