""" Main Module """
from scripts.db import NeonDB

db = NeonDB()

db.run_sql_file("scripts/sql/clear_tables.sql")
db.run_sql_file("scripts/sql/synthetic_population.sql")
