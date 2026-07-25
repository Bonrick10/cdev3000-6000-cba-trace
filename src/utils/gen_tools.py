"""
Synthetic transaction generation utilities.

This module provides helper functions for generating realistic
transactional behaviour tied to merchant categories, timestamps,
locations, device usage, and receiver selection.

All functions are designed to be deterministic in structure but
probabilistic in output, suitable for synthetic data pipelines.
"""

import random
import secrets
from datetime import datetime, timedelta
from typing import Dict, Tuple, List, Any
from utils.db import NeonDB
from utils.txn_gen_tools import mer_tools, p2p_tools, loc_tools, device_tools 

THRESHOLD_LOW_TXNS = 5
THRESHOLD_YOUNG_ACC = timedelta(days=15)

def gen_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, devices, timestamp, db):
    """
    Generate a transaction based on the seed account and its history.
    """
    r = random.random()

    if r < 0.004:
        gen_sus_txn(seed_account, seed_acc_txns, accounts, merchants, devices, timestamp, db)
    elif r < 0.010:
        gen_unusual_txn(seed_account, seed_acc_txns, accounts, merchants, devices, timestamp, db)
    else:
        gen_legit_txn(seed_account, seed_acc_txns, accounts, merchants, devices, timestamp, db)

def gen_legit_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, devices, timestamp, db):
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
    if len(seed_acc_txns) < THRESHOLD_LOW_TXNS or age < THRESHOLD_YOUNG_ACC:
        r = random.random()
        if r < 0.80:
            receiver_bsb, receiver_acc, merchant_tag, amount = mer_tools.choose_any_merchant_receiver(
                seed_account=seed_account,
                merchants=merchants
        )
        else:
            receiver_bsb, receiver_acc, amount = p2p_tools.choose_any_p2p_receiver(
                seed_account=seed_account,
                accounts=accounts
            )
            merchant_tag = None
    
        lat, lon = loc_tools.gen_rand_loc(seed_account)
        device_id = device_tools.choose_any_device(seed_account, devices)

    else:
        r = random.random()
        if r < 0.80:
            receiver_bsb, receiver_acc, merchant_tag, amount = mer_tools.choose_known_merchant_receiver(
                seed_account=seed_account,
                seed_acc_txns=seed_acc_txns,
                merchants=merchants
        )
        else:
            receiver_bsb, receiver_acc, amount = p2p_tools.choose_known_p2p_receiver(
                seed_account=seed_account,
                seed_acc_txns=seed_acc_txns,
                accounts=accounts
            )
            merchant_tag = None
        lat, lon = loc_tools.gen_near_loc(seed_account, seed_acc_txns)
        device_id = device_tools.choose_known_device(seed_account, seed_acc_txns, devices)
    
    txn = {
        "sender_bsb": seed_account.bsb,
        "sender_account_number": seed_account.account_number,
        "receiver_bsb": receiver_bsb,
        "receiver_account_number": receiver_acc,
        "amount": amount,
        "transaction_time": timestamp["txn_time"],
        "sender_latitude": lat,
        "sender_longitude": lon,
        "label": "legitimate",
        "merchant_tags": merchant_tag,
        "device_id": device_id
    }
    insert_txn(txn, db)

def gen_unusual_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, devices, timestamp, db):
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
        
        merchant_data = get_merchant_data(receiver.merchant_tag)
        if receiver["is_merchant"]:
            merchant_tag = receiver["merchant_tag"]
            _, _, sus_min_amt, min_amt, max_amt, sus_max_amt = merchant_data
            amount = round(random.uniform(min_amt, max_amt), 2)
        else:
            merchant_tag = None
            amount = round(random.uniform(5, 500), 2)
    else:
        r = random.random()
        if r < 0.80:
            receiver_bsb, receiver_acc, merchant_tag, amount = mer_tools.choose_known_merchant_receiver(
                seed_account=seed_account,
                seed_acc_txns=seed_acc_txns,
                merchants=merchants
        )
        else:
            receiver_bsb, receiver_acc, amount = p2p_tools.choose_known_p2p_receiver(
                seed_account=seed_account,
                seed_acc_txns=seed_acc_txns,
                accounts=accounts
            )
            merchant_tag = None

    # 30% chance of unusual location
    if random.random() < 0.3:
        lat, lon = loc_tools.gen_unusual_loc(seed_account)
    else:
        lat, lon = loc_tools.gen_normal_loc(seed_account)

    # 20% chance of unseen device
    if random.random() < 0.2:
        device_id = generate_random_device_id()
    else:
        device_id = choose_device_from_seed(seed_account, devices)

    return {
       "sender_bsb": seed_account["bsb"],
        "sender_account_number": seed_account["account_number"],
        "receiver_bsb": receiver_bsb,
        "receiver_account_number": receiver_acc,
        "amount": amount,
        "transaction_time": timestamp["txn_time"],
        "sender_latitude": lat,
        "sender_longitude": lon,
        "label": "suspicious",
        "merchant_tags": merchant_tag,
        "device_id": device_id
    }

def gen_sus_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, devices, timestamp, db):
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

    if random.random() > 0.6:
        receiver_bsb, receiver_acc, merchant_tag, amount = mer_tools.choose_known_merchant_receiver(
            seed_account=seed_account,
            seed_acc_txns=seed_acc_txns,
            merchants=merchants
        )
    else:
        receiver_bsb, receiver_acc, amount = p2p_tools.choose_known_p2p_receiver(
            seed_account=seed_account,
            seed_acc_txns=seed_acc_txns,
            accounts=accounts
        )
        merchant_tag = None

    # force large amount

    merchant_data = get_merchant_data(merchant_tag)
    min_amt, max_amt, _ = merchant_data
    amount = round(random.uniform(max_amt * 0.7, max_amt), 2)

    # force new payee
    receiver = random.choice(accounts)
    receiver_bsb, receiver_acc = receiver["bsb"], receiver["account_number"]

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
        "sender_bsb": seed_account["bsb"],
        "sender_account_number": seed_account["account_number"],
        "receiver_bsb": receiver_bsb,
        "receiver_account_number": receiver_acc,
        "amount": amount,
        "transaction_time": timestamp,
        "sender_latitude": lat,
        "sender_longitude": lon,
        "label": "suspicious",
        "merchant_tags": merchant_tag,
        "device_id": device_id
    }

def get_merchant_data(merchant_tag):
    """
    Fetch merchant amount limits from the database.
    """
    db = NeonDB()
    merchant_data = db.query(
        """
        SELECT 
            suspicious_threshold_lower, 
            usual_threshold_lower, 
            usual_threshold_upper, 
            suspicious_threshold_upper 
        FROM merchant_tags WHERE merchant_tag = %s LIMIT 1;
        """, (merchant_tag))
    return merchant_data

# ---------------------------------------------------------------------------
# Merchant tag selection
# ---------------------------------------------------------------------------

def choose_merchant_tag(merchant_tags: List[str]) -> str:
    """
    Select a merchant tag with weighted probability.

    Args:
        merchant_tags: List of merchant tag names.

    Returns:
        A single merchant tag name.
    """
    weights = [0.4, 0.2, 0.2, 0.1, 0.1]
    return random.choices(merchant_tags, weights=weights, k=1)[0]


# ---------------------------------------------------------------------------
# Amount generation tied to merchant tag
# ---------------------------------------------------------------------------

def generate_amount_for_tag(tag_name: str) -> float:
    """
    Generate a realistic transaction amount based on merchant category.

    Args:
        tag_name: Merchant category name.

    Returns:
        A float representing the transaction amount.
    """
    profile = MERCHANT_AMOUNT_PROFILES.get(tag_name)

    if profile is None:
        return round(random.uniform(10, 300), 2)

    min_amt, max_amt, small_bias = profile
    midpoint = (min_amt + max_amt) / 2

    if random.random() < small_bias:
        return round(random.uniform(min_amt, midpoint), 2)

    return round(random.uniform(midpoint, max_amt), 2)


# ---------------------------------------------------------------------------
# Timestamp generation
# ---------------------------------------------------------------------------

def generate_timestamp() -> datetime:
    """
    Generate a realistic timestamp for a transaction.

    Returns:
        A datetime object representing the transaction time.
    """
    weekday_bias = random.random() < 0.8
    day_offset = random.randint(0, 4) if weekday_bias else random.randint(5, 6)

    base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    date = base_date + timedelta(days=day_offset)

    r2 = random.random()
    if r2 < 0.80:
        hour = random.randint(7, 21)
    elif r2 < 0.95:
        hour = random.randint(5, 6)
    else:
        hour = random.randint(22, 23)

    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    return date.replace(hour=hour, minute=minute, second=second)


# ---------------------------------------------------------------------------
# Receiver selection
# ---------------------------------------------------------------------------

def choose_receiver(seed_account: Any,
                    accounts: List[Any],
                    merchants: List[Any]) -> Tuple[int, int]:
    """
    Select a receiver for a transaction.

    Args:
        seed_account: The sender account object.
        accounts: List of all accounts.
        merchants: List of merchant account objects.

    Returns:
        Tuple of (receiver_bsb, receiver_account_number).
    """
    r = random.random()

    if r < 0.40:
        merchant = random.choice(merchants)
        return merchant.bsb, merchant.account_number

    if r < 0.70:
        return seed_account.bsb, random.choice(seed_account.other_accounts)

    other = random.choice(accounts)
    return other.bsb, other.account_number

def get_known_payees(db, seed_account) -> set:
    sender_bsb = seed_account.bsb
    sender_acc = seed_account.account_number
    
    db = NeonDB()

    rows = db.query(
        """
        SELECT DISTINCT receiver_bsb, receiver_account_number
        FROM transactions
        WHERE sender_bsb = %(bsb)s
          AND sender_account_number = %(acc)s;
        """,
        {"bsb": sender_bsb, "acc": sender_acc}
    )

    return {(row["receiver_bsb"], row["receiver_account_number"]) for row in rows}

def split_payees(accounts, known_payees):
    known = []
    new = []

    for acc in accounts:
        key = (acc.bsb, acc.account_number)
        if key in known_payees:
            known.append(acc)
        else:
            new.append(acc)

    return known, new

# ---------------------------------------------------------------------------
# Location generation
# ---------------------------------------------------------------------------

def generate_location(seed_account: Any) -> Tuple[float, float]:
    """
    Generate a realistic location for a transaction.

    Args:
        seed_account: Account object containing home/work locations.

    Returns:
        Tuple of (latitude, longitude).
    """
    r = random.random()
    home_lat, home_lon = seed_account.home_location
    work_lat, work_lon = seed_account.work_location

    if r < 0.70:
        return (
            home_lat + random.uniform(-0.01, 0.01),
            home_lon + random.uniform(-0.01, 0.01),
        )

    if r < 0.95:
        return (
            work_lat + random.uniform(-0.02, 0.02),
            work_lon + random.uniform(-0.02, 0.02),
        )

    return (
        home_lat + random.uniform(-0.5, 0.5),
        home_lon + random.uniform(-0.5, 0.5),
    )


# ---------------------------------------------------------------------------
# Device selection
# ---------------------------------------------------------------------------

def choose_device(seed_account: Any, devices: List[Any]) -> str:
    """
    Select a device ID for a transaction.

    Args:
        seed_account: Account object containing device IDs.

    Returns:
        A device ID string.
    """
    r = random.random()

    # TODO: Implement logic to select a device based on known devices and probabilities.
    # For now, we will randomly select a device from the provided list.
    # 90% chance of using a previous device, 8% chance of using a new device, 2% chance of using a random device
    if r < 0.90:
        return random.choice(devices).device_id

    if r < 0.98:
        return random.choice(devices).device_id

    return random.choice(devices).device_id


def generate_random_device_id() -> str:
    """
    Generate a random 64-character hex device ID.

    Returns:
        A device ID string.
    """
    return secrets.token_hex(32)

# ----------------------------------------------------------------------------
# Transaction Insertion
# ----------------------------------------------------------------------------
def insert_txn(txn: Dict[str, Any], db: NeonDB) -> None:
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