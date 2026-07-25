""" Data Population Module """
from pathlib import Path
import random
from datetime import datetime, timedelta
from utils.db import NeonDB
from rules.rules import check_rules
import utils.gen_tools as gen_tools

BASE_DIR = Path(__file__).resolve().parent
SQL_DIR = BASE_DIR / "sql"
SRC_DIR = BASE_DIR.parent
UTILS_DIR = SRC_DIR / "utils"

def generate_seed_data():
    """
    Populates the database with synthetic data.
    """
    db = NeonDB()
    db.execute(db.read_sql_file(SQL_DIR / "clear_tables.sql"))
    db.execute(db.read_sql_file(SQL_DIR / "synthetic_population.sql"))

def gen_all_txns():
    db = NeonDB()
    db.execute(db.read_sql_file(UTILS_DIR / "sql" / "timeline.sql"))
    
    timeline = db.query("SELECT txn_time FROM synthetic_timeline ORDER BY txn_time;")
    accounts = db.query("SELECT * FROM accounts WHERE is_merchant = FALSE;")
    merchants = db.query("SELECT * FROM accounts WHERE is_merchant = TRUE;")
    devices = db.query("SELECT * FROM devices;")
    merchant_tags = db.query("""
        SELECT
            merchant_tags.id,
            merchant_tags.merchant_category,
            merchant_tags.suspicious_threshold_lower::numeric AS suspicious_threshold_lower,
            merchant_tags.usual_threshold_lower::numeric AS usual_threshold_lower,
            merchant_tags.usual_threshold_upper::numeric AS usual_threshold_upper,
            merchant_tags.suspicious_threshold_upper::numeric AS suspicious_threshold_upper
        FROM merchant_tags
    """)
    devices = db.query("SELECT DISTINCT device_id FROM device_sessions;")

    for timestamp in timeline:
        seed_account = random.choice(accounts)
        seed_acc_txns = db.query(
            """
            SELECT * FROM transactions WHERE sender_bsb = %(bsb)s AND sender_account_number = %(acc)s ORDER BY transaction_time DESC;
            """,
            {"bsb": seed_account["bsb"], "acc": seed_account["account_number"]}
        )
        gen_tools.gen_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, devices, timestamp, db)


def maybe_gen_correction(transaction, db):
    # 0.1% chance of correction
    if random.random() > 0.001:
        return None

    old_label = transaction["label"]

    if old_label == "legitimate" or old_label == "unusual" or old_label == "suspicious":
        new_label = random.choice(["confirmed_legitimate", "confirmed_fraud"])

    
    # Correction timing
    day_delta = timedelta(days=random.randint(3, 60))
    hour_delta = timedelta(hours=random.randint(0, 23))
    minute_delta = timedelta(minutes=random.randint(0, 59))
    delta = day_delta + hour_delta + minute_delta

    correction_time = transaction["transaction_time"] + delta

    correction = {
        "transaction_id": transaction["id"],
        "old_label": old_label,
        "new_label": new_label,
        "correction_time": correction_time
    }
    db.execute(
        """
        INSERT INTO corrections (transaction_id, old_label, new_label, correction_time) 
        VALUES (%(transaction_id)s, %(old_label)s, %(new_label)s, %(correction_time)s)
        """, correction)