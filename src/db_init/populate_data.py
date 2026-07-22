""" Data Population Module """
from pathlib import Path
import random
from datetime import datetime, timedelta
from utils.db import NeonDB
from rules.rules import check_rules
import utils.generator_tools as gen_tools

BASE_DIR = Path(__file__).resolve().parent
SQL_DIR = BASE_DIR / "sql"


def generate_seed_data():
    """
    Populates the database with synthetic data.
    """
    db = NeonDB()
    db.run_sql_file(SQL_DIR / "clear_tables.sql")
    db.run_sql_file(SQL_DIR / "synthetic_population.sql")

def generate_transaction(seed_account, accounts, merchants, devices):
    r = random.random()

    if r < 0.004:
        txn = generate_suspicious_transaction(seed_account, accounts, merchants, devices)
    elif r < 0.010:
        txn = generate_unusual_transaction(seed_account, accounts, merchants, devices)
    else:
        txn = generate_legitimate_transaction(seed_account, accounts, merchants, devices)

    txn["label"] = check_rules(txn, dryrun_flag=True).value
    return txn

def generate_legitimate_transaction(seed_account, accounts, merchants, devices):
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
    
    r = random.random()
    if r < 0.80:
        receiver_bsb, receiver_acc, merchant_tag, amount = gen_tools.choose_merchant_receiver(
            seed_account=seed_account,
            merchants=merchants
        )
    else:
        receiver_bsb, receiver_acc, amount = gen_tools.choose_p2p_receiver(
            seed_account=seed_account,
            accounts=accounts
        )
        merchant_tag = None
    
    lat, lon = gen_tools.generate_location(seed_account)
    timestamp = gen_tools.generate_timestamp()
    device_id = gen_tools.choose_device(seed_account, devices)

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

def generate_unusual_transaction(seed_account, accounts, merchants, devices):
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
    else:
        receiver_bsb, receiver_acc = choose_receiver(seed_account, accounts, merchants)

    # 30% chance of unusual location
    if random.random() < 0.3:
        lat = seed_account.home_location[0] + random.uniform(-0.1, 0.1)
        lon = seed_account.home_location[1] + random.uniform(-0.1, 0.1)
    else:
        lat, lon = gen_tools.generate_location(seed_account)

    # unusual time-of-day
    timestamp = datetime.now().replace(
        hour=random.choice([1, 2, 3, 4, 23]),
        minute=random.randint(0, 59),
        second=random.randint(0, 59)
    )

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
        "transaction_time": timestamp,
        "sender_latitude": lat,
        "sender_longitude": lon,
        "merchant_tags": merchant_tag,
        "device_id": device_id
    }

def generate_suspicious_transaction(seed_account, accounts, merchants, merchant_tags):
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
