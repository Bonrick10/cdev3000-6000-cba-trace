"""Database connection utilities for Neon/Postgres."""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import sys

load_dotenv()
class NeonDB:
    """
    Wrapper for connecting to Neon/Postgres using psycopg2.
    """
    def __init__(self, db_url=None):
        """
        Initialize the NeonDB instance and load the database URL.
        """

        self.db_url = db_url or os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable is not set.")

    def connect(self):
        """
        Connects to the Neon/Postgres database.
        """
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def read_sql_file(self, filepath):
        """
        Reads an SQL file into a string and returns it
        Can then be passed into query() and execute()
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"SQL file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            sql = f.read()
            return sql

    def query(self, sql, params=None):
        """
        Runs a SELECT query and returns results as Python dicts.
        """
        conn = self.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()
        finally:
            conn.close()

    def execute(self, sql, params=None):
        """
        Runs INSERT/UPDATE/DELETE queries.
        """
        conn = self.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
            conn.commit()
            print(f"[OK] Executed SQL file: {filepath}")
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] SQL execution failed: {e}", file=sys.stderr)
            raise
        finally:
            conn.close()
