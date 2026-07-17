""" Data Population Module """
from utils.db import NeonDB
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SQL_DIR = BASE_DIR / "sql"


def populate_data():
    """
    Populates the database with synthetic data.
    """
    db = NeonDB()
    db.run_sql_file(SQL_DIR / "clear_tables.sql")
    db.run_sql_file(SQL_DIR / "synthetic_population.sql")