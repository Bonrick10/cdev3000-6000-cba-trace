""" Data Population Module """
from pathlib import Path
import random
from datetime import datetime, timedelta, timezone
from utils.db import NeonDB
import db_init.gen_tools as gen_tools

BASE_DIR = Path(__file__).resolve().parent
SQL_DIR = BASE_DIR / "sql"
SRC_DIR = BASE_DIR.parent
BASE_TIME = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc) # 2023-01-01 00:00:00+00
END_TIME = datetime(2026, 6, 30, 23, 59, 59, tzinfo=timezone.utc) # 2026-06-30 23:59:59+00

def generate_seed_data():
    """
    Populates the database with synthetic data.
    """
    db = NeonDB()
    print("Resetting database")
    db.execute(db.read_sql_file(SQL_DIR / "clear_tables.sql"))
    print("Generating data")
    db.execute(db.read_sql_file(SQL_DIR / "synthetic_population.sql"))

def gen_all_txns():
    db = NeonDB()
    
    # RIP Memory usage 💀
    # Array of account dicts
    accounts = db.query("SELECT * FROM accounts WHERE is_merchant = FALSE;")
    # Array of account dicts
    merchants = db.query("SELECT * FROM accounts WHERE is_merchant = TRUE;")
    # Dict mapping merchant_tags.id to merchant_tag
    merchant_tags = { merchant_tag["id"]: merchant_tag for merchant_tag in 
        db.query("""
        SELECT
            merchant_tags.id,
            merchant_tags.merchant_category,
            merchant_tags.suspicious_threshold_lower::numeric AS suspicious_threshold_lower,
            merchant_tags.usual_threshold_lower::numeric AS usual_threshold_lower,
            merchant_tags.usual_threshold_upper::numeric AS usual_threshold_upper,
            merchant_tags.suspicious_threshold_upper::numeric AS suspicious_threshold_upper
        FROM merchant_tags
        """)
    }
    # Array of device_ids
    device_sessions = db.query("SELECT * FROM device_sessions;")
    
    # Key is tuple of (bsb, account_number) value is arr of transaction dicts
    # (should be ascending time ordered since insert in order of timeline)
    account_txns = {(account["bsb"], account["account_number"]): [] for account in accounts}

    timeline = gen_tools.gen_timeline(BASE_TIME, END_TIME)

    print("Generating Transaction Data")
    for index, new_txn_time in enumerate(timeline):
        seed_account = random.choice(accounts)
        seed_acc_txns = account_txns[(seed_account["bsb"], seed_account["account_number"])]

        print(f"\rGenerating Transaction {index} of {len(timeline)}")
        new_txns = gen_tools.gen_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, device_sessions, new_txn_time, db)
        for new_txn in new_txns:
            account_txns[(seed_account["bsb"], seed_account["account_number"])].append(new_txn)
            insert_txn(new_txn, db) 

# def maybe_gen_correction(transaction, db):
#     # 0.1% chance of correction
#     if random.random() > 0.001:
#         return None

#     old_label = transaction["label"]

#     if old_label == "legitimate" or old_label == "unusual" or old_label == "suspicious":
#         new_label = random.choice(["confirmed_legitimate", "confirmed_fraud"])

    
#     # Correction timing
#     day_delta = timedelta(days=random.randint(3, 60))
#     hour_delta = timedelta(hours=random.randint(0, 23))
#     minute_delta = timedelta(minutes=random.randint(0, 59))
#     delta = day_delta + hour_delta + minute_delta

#     correction_time = transaction["transaction_time"] + delta

#     correction = {
#         "transaction_id": transaction["id"],
#         "old_label": old_label,
#         "new_label": new_label,
#         "correction_time": correction_time
#     }
#     db.execute(
#         """
#         INSERT INTO corrections (transaction_id, old_label, new_label, correction_time) 
#         VALUES (%(transaction_id)s, %(old_label)s, %(new_label)s, %(correction_time)s)
#         """, correction)

def insert_txn(txn, db):
    """
    Insert a transaction into the database.

    Args:
        txn: Dictionary containing transaction details.
        db: NeonDB instance for database operations.
    """
    db.execute(
        """
        INSERT INTO transactions (
            sender_bsb,
            sender_account_number,
            receiver_bsb,
            receiver_account_number,
            amount,
            transaction_time,
            sender_latitude,
            sender_longitude,
            label,
            merchant_tags,
            device_id
        ) VALUES (
            %(sender_bsb)s,
            %(sender_account_number)s,
            %(receiver_bsb)s,
            %(receiver_account_number)s,
            %(amount)s,
            %(transaction_time)s,
            %(sender_latitude)s,
            %(sender_longitude)s,
            %(label)s,
            %(merchant_tags)s,
            %(device_id)s
        );
        """,
        txn
    )