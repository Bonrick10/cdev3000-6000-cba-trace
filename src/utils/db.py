<<<<<<< HEAD
"""Database connection utilities for Neon/Postgres."""

import os
import sys
=======
"""Small, shared database boundary for Neon/PostgreSQL."""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Optional
>>>>>>> cb9cd5a8bd1209222dfe2d28609f9f202e9ac8b9

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv()
<<<<<<< HEAD
=======


class NeonDB:
    """
    Wrapper for connecting to Neon/Postgres using psycopg2.
    """

    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize the NeonDB instance and load the database URL.
        """
>>>>>>> cb9cd5a8bd1209222dfe2d28609f9f202e9ac8b9


class NeonDB:
    """Wrapper for connecting to Neon/Postgres using psycopg2.
    """

    def __init__(self, db_url=None):
        """Initialize the NeonDB instance and load the database URL.
        """
        self.db_url = db_url or os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable is not set.")

    def connect(self):
        """Connects to the Neon/Postgres database.
        """
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

<<<<<<< HEAD
    def read_sql_file(self, filepath):
        """Reads an SQL file into a string and returns it
=======
    @staticmethod
    def read_sql_file(filepath):
        """
        Reads an SQL file into a string and returns it
>>>>>>> cb9cd5a8bd1209222dfe2d28609f9f202e9ac8b9
        Can then be passed into query() and execute()
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"SQL file not found: {filepath}")
        return path.read_text(encoding="utf-8")

    @contextmanager
    def transaction(self):
        """Yield one connection and commit or roll it back atomically."""
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

<<<<<<< HEAD
    def query(self, sql, params=None):
        """Runs a SELECT query and returns results as Python dicts.
=======
    def query(self, sql, params=None, connection=None):
        """
        Runs a SELECT query and returns results as Python dicts.
>>>>>>> cb9cd5a8bd1209222dfe2d28609f9f202e9ac8b9
        """
        conn = connection or self.connect()
        owns_connection = connection is None
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()
        finally:
            if owns_connection:
                conn.close()

<<<<<<< HEAD
    def execute(self, sql, params=None):
        """Runs INSERT/UPDATE/DELETE queries.
=======
    def execute(self, sql, params=None, connection=None):
        """
        Runs INSERT/UPDATE/DELETE queries.
>>>>>>> cb9cd5a8bd1209222dfe2d28609f9f202e9ac8b9
        """
        conn = connection or self.connect()
        owns_connection = connection is None
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall() if cur.description else []
            if owns_connection:
                conn.commit()
            return rows
        except Exception:
            if owns_connection:
                conn.rollback()
            raise
        finally:
            if owns_connection:
                conn.close()

    def query_sql_file(self, filepath, params=None, connection=None):
        """Execute a SELECT stored in a SQL file."""
        return self.query(self.read_sql_file(filepath), params, connection)

    def execute_sql_file(self, filepath, params=None, connection=None):
        """Execute a write statement stored in a SQL file."""
        return self.execute(self.read_sql_file(filepath), params, connection)

    def run_sql_file(self, filepath, params=None, fetch=False, connection=None):
        """Compatibility helper for earlier repository call sites."""
        method = self.query_sql_file if fetch else self.execute_sql_file
        return method(filepath, params, connection)
