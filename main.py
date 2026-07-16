""" Main Module """
from scripts.db import NeonDB

db = NeonDB("postgresql://neondb_owner:npg_sg64fyOpzPvx@ep-autumn-night-a7q6iqvr-pooler.ap-southeast-2.aws.neon.tech/neondb?channel_binding=require&sslmode=require")

db.run_sql_file("scripts/sql/clear_tables.sql")
db.run_sql_file("scripts/sql/synthetic_population.sql")
