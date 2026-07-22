""" Data Population Module """
from pathlib import Path
import random
from datetime import datetime, timedelta
from utils.db import NeonDB
from rules.rules import check_rules
import utils.generator_tools as gen_tools

BASE_DIR = Path(__file__).resolve().parent
SQL_DIR = BASE_DIR / "sql"
SRC_DIR = BASE_DIR.parent
UTILS_DIR = SRC_DIR / "utils"

THRESHOLD_LOW_TXNS = 5
THRESHOLD_YOUNG_ACC = timedelta(days=15)

def generate_seed_data():
    """
    Populates the database with synthetic data.
    """
    db = NeonDB()
    db.run_sql_file(SQL_DIR / "clear_tables.sql")
    db.run_sql_file(SQL_DIR / "synthetic_population.sql")

def gen_all_txns():
    db = NeonDB()
    db.run_sql_file(UTILS_DIR / "sql" / "timeline.sql")
    
    timeline = db.query("SELECT txn_time FROM synthetic_timeline ORDER BY txn_time;")
    accounts = db.query("SELECT * FROM accounts WHERE is_merchant = FALSE;")
    merchants = db.query("SELECT * FROM accounts WHERE is_merchant = TRUE;")
    devices = db.query("SELECT * FROM devices;")

    for timestamp in timeline:
        seed_account = random.choice(accounts)
        seed_acc_txns = db.query(
            """
            SELECT * FROM transactions WHERE sender_bsb = %(bsb)s AND sender_account_number = %(acc)s ORDER BY transaction_time DESC;
            """,
            {"bsb": seed_account.bsb, "acc": seed_account.account_number}
        )
        gen_txn(seed_account, seed_acc_txns, accounts, merchants, devices, timestamp, db)


def gen_txn(seed_account, seed_acc_txns, accounts, merchants, devices, timestamp, db):
    r = random.random()

    if r < 0.004:
        gen_sus_txn(seed_account, seed_acc_txns, accounts, merchants, devices, timestamp, db)
    elif r < 0.010:
        gen_unusual_txn(seed_account, seed_acc_txns, accounts, merchants, devices, timestamp, db)
    else:
        gen_legit_txn(seed_account, seed_acc_txns, accounts, merchants, devices, timestamp, db)

def gen_legit_txn(seed_account, seed_acc_txns, accounts, merchants, devices, timestamp, db):
    """
    Generate a realistic legitimate transaction.
    Behaviour:
    - normal merchant categories
    - normal amounts
    - normal device
    - normal location cluster
    - normal time-of-day
    - known payees (?)
    """

    first_txn_time = seed_acc_txns[-1]["transaction_time"] if len(seed_acc_txns) > 0 else timestamp["txn_time"]
    age = timestamp["txn_time"] - first_txn_time
    if len(seed_acc_txns) > THRESHOLD_LOW_TXNS or age > THRESHOLD_YOUNG_ACC:
        r = random.random()
        if r < 0.80:
            receiver_bsb, receiver_acc, merchant_tag, amount = gen_tools.choose_any_merchant_receiver(
                seed_account=seed_account,
                merchants=merchants
        )
        else:
            receiver_bsb, receiver_acc, amount = gen_tools.choose_any_p2p_receiver(
                seed_account=seed_account,
                accounts=accounts
            )
            merchant_tag = None
    
        lat, lon = gen_tools.gen_rand_loc(seed_account)
        device_id = gen_tools.choose_any_device(seed_account, devices)

    else:
        r = random.random()
        if r < 0.80:
            receiver_bsb, receiver_acc, merchant_tag, amount = gen_tools.choose_known_merchant_receiver(
                seed_account=seed_account,
                seed_acc_txns=seed_acc_txns,
                merchants=merchants
        )
        else:
            receiver_bsb, receiver_acc, amount = gen_tools.choose_known_p2p_receiver(
                seed_account=seed_account,
                seed_acc_txns=seed_acc_txns,
                accounts=accounts
            )
            merchant_tag = None
        lat, lon = gen_tools.gen_near_loc(seed_account, seed_acc_txns)
        device_id = gen_tools.choose_known_device(seed_account, seed_acc_txns, devices)
    
    txn = {
        "sender_bsb": seed_account.bsb,
        "sender_account_number": seed_account.account_number,
        "receiver_bsb": receiver_bsb,
        "receiver_account_number": receiver_acc,
        "amount": amount,
        "transaction_time": timestamp["txn_time"],
        "sender_latitude": lat,
        "sender_longitude": lon,
        "merchant_tags": merchant_tag,
        "device_id": device_id
    }
    gen_tools.insert_txn(txn, db)

def gen_unusual_txn(seed_account, seed_acc_txns, accounts, merchants, devices, timestamp, db):
    """
    Generate a mildly abnormal transaction.
    Behaviour:
    - new device OR new payee OR slightly large amount
    - slightly unusual merchant category
    - slightly unusual location (work or small travel)
    - unusual time-of-day (early morning or late night)
    """

    
    # 50% chance of new payee
    if random.random() < 0.5:
        receiver = random.choice(accounts)
        receiver_bsb, receiver_acc = receiver.bsb, receiver.account_number
        if receiver.is_merchant:
            merchant_tag = receiver.merchant_category
            min_amt, max_amt, _ = gen_tools.MERCHANT_AMOUNT_PROFILES[merchant_tag]
            amount = round(random.uniform(min_amt, max_amt), 2)
        else:
            merchant_tag = None
            amount = round(random.uniform(5, 500), 2)
    else:
        r = random.random()
        if r < 0.80:
            receiver_bsb, receiver_acc, merchant_tag, amount = gen_tools.choose_known_merchant_receiver(
                seed_account=seed_account,
                seed_acc_txns=seed_acc_txns,
                merchants=merchants
        )
        else:
            receiver_bsb, receiver_acc, amount = gen_tools.choose_known_p2p_receiver(
                seed_account=seed_account,
                seed_acc_txns=seed_acc_txns,
                accounts=accounts
            )
            merchant_tag = None

    # 30% chance of unusual location
    if random.random() < 0.3:
        lat = seed_account.home_location[0] + random.uniform(-0.1, 0.1)
        lon = seed_account.home_location[1] + random.uniform(-0.1, 0.1)
    else:
        lat, lon = gen_tools.generate_location(seed_account)

    # 20% chance of unseen device
    if random.random() < 0.2:
        device_id = gen_tools.generate_random_device_id()
    else:
        device_id = gen_tools.choose_device_from_seed(seed_account, devices)

    return {
        "sender_bsb": seed_account.bsb,
        "sender_account_number": seed_account.account_number,
        "receiver_bsb": receiver_bsb,
        "receiver_account_number": receiver_acc,
        "amount": amount,
        "transaction_time": timestamp["txn_time"],
        "sender_latitude": lat,
        "sender_longitude": lon,
        "merchant_tags": merchant_tag,
        "device_id": device_id
    }

def gen_sus_txn(seed_account, seed_acc_txns, accounts, merchants, devices, timestamp, db):
    """
    Generate a rule-breaking suspicious transaction.
    Behaviour:
    - impossible travel (far location)
    - very large amount
    - new payee
    - unseen device
    - suspicious merchant category
    - unusual time-of-day
    """
    merchant_tag = random.choice(suspicious_tags)

    # force large amount
    min_amt, max_amt, _ = MERCHANT_AMOUNT_PROFILES[merchant_tag]
    amount = round(random.uniform(max_amt * 0.7, max_amt), 2)

    # force new payee
    receiver = random.choice(accounts)
    receiver_bsb, receiver_acc = receiver.bsb, receiver.account_number

    # impossible travel: far outside normal cluster
    lat = seed_account.home_location[0] + random.uniform(5.0, 25.0)
    lon = seed_account.home_location[1] + random.uniform(5.0, 25.0)

    # suspicious time-of-day
    timestamp = datetime.now().replace(
        hour=random.choice([0, 1, 2, 3]),
        minute=random.randint(0, 59),
        second=random.randint(0, 59)
    )

    # unseen device
    device_id = generate_random_device_id()

    return {
        "sender_bsb": seed_account.bsb,
        "sender_account_number": seed_account.account_number,
        "receiver_bsb": receiver_bsb,
        "receiver_account_number": receiver_acc,
        "amount": amount,
        "transaction_time": timestamp,
        "sender_latitude": lat,
        "sender_longitude": lon,
        "merchant_tags": merchant_tag,
        "device_id": device_id
    }


def maybe_gen_correction(transaction):
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
