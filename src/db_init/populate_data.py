""" Data Population Module """
from pathlib import Path
import random
from utils.db import NeonDB

BASE_DIR = Path(__file__).resolve().parent
SQL_DIR = BASE_DIR / "sql"


def generate_seed_data():
    """
    Populates the database with synthetic data.
    """
    db = NeonDB()
    db.run_sql_file(SQL_DIR / "clear_tables.sql")
    db.run_sql_file(SQL_DIR / "synthetic_population.sql")

def generate_transaction(seed_account, merchants, devices):
    txn_time = generate_timestamp()
    sender = seed_account
    receiver = choose_receiver(seed_account)

    lat, lon = generate_location(seed_account)

    merchant_tag = choose_merchant_tag()
    merchant_tag_name = merchant_tag.name
    amount = generate_amount_for_tag(merchant_tag_name)

    device_id = choose_device(seed_account)

    label = "non_fraud"

    return {
        "sender_bsb": sender.bsb,
        "sender_account_number": sender.account_number,
        "receiver_bsb": receiver.bsb,
        "receiver_account_number": receiver.account_number,
        "amount": amount,
        "transaction_time": txn_time,
        "sender_latitude": lat,
        "sender_longitude": lon,
        "label": label,
        "merchant_tags": merchant_tag,
        "device_id": device_id
    }


def maybe_generate_correction(transaction):
    # 0.1% chance of correction
    if random.random() > 0.001:
        return None

    old_label = transaction["label"]

    # Mostly fraud → non_fraud corrections
    if old_label == "fraud":
        new_label = "legitimate"
    else:
        new_label = "fraud"

    # Correction timing
    r = random.random()
    if r < 0.70:
        delta = timedelta(minutes=random.randint(5, 120))
    elif r < 0.90:
        delta = timedelta(hours=random.randint(2, 24))
    else:
        delta = timedelta(days=random.randint(1, 3))

    correction_time = transaction["transaction_time"] + delta

    return {
        "transaction_id": transaction["id"],
        "old_label": old_label,
        "new_label": new_label,
        "correction_time": correction_time
    }
