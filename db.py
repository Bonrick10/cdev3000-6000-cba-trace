""" Database Interface """

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv() # load local environment variables from .env

conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

def get_transaction(sender_id):
    """Get list of transaction details for a specified sender id"""
    cur.execute("""
        SELECT *
        FROM transactions
        WHERE sender_id = %s
    """, [sender_id])
    print(cur.fetchall())
    return cur.fetchall()
