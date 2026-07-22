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

# ---------------------------------------------------------------------------
# Merchant amount profiles
# ---------------------------------------------------------------------------

MERCHANT_AMOUNT_PROFILES: Dict[str, Tuple[int, int, float]] = {
    "Groceries": (10, 250, 0.70),
    "Fuel Station": (20, 180, 0.80),
    "Restaurant": (10, 200, 0.85),
    "Fast Food": (5, 40, 0.95),
    "Coffee Shop": (3, 25, 0.98),
    "Department Store": (20, 600, 0.70),
    "Electronics": (50, 2500, 0.40),
    "Online Marketplace": (10, 800, 0.60),
    "Pharmacy": (5, 150, 0.85),
    "Medical Services": (40, 600, 0.50),
    "Hospital": (200, 10000, 0.20),
    "Hotel": (100, 1200, 0.30),
    "Airline": (100, 2500, 0.20),
    "Public Transport": (2, 30, 0.95),
    "Taxi/Rideshare": (8, 120, 0.85),
    "Subscription Service": (5, 80, 0.90),
    "Streaming Service": (5, 40, 0.95),
    "Utility Bills": (30, 400, 0.60),
    "Telecommunications": (20, 200, 0.70),
    "Insurance": (50, 700, 0.50),
    "Government Services": (20, 1000, 0.40),
    "Education": (50, 3000, 0.30),
    "Charity": (5, 250, 0.80),
    "ATM Withdrawal": (20, 500, 0.70),
    "Cash Advance": (50, 800, 0.50),
    "Jewellery": (100, 5000, 0.30),
    "Luxury Retail": (200, 4000, 0.20),
    "Gaming": (5, 100, 0.85),
    "Liquor Store": (10, 150, 0.85),
    "Hardware Store": (20, 800, 0.60),
    "Home Improvement": (50, 3000, 0.40),
    "Pet Supplies": (10, 250, 0.75),
    "Sporting Goods": (20, 700, 0.60),
    "Beauty & Cosmetics": (10, 250, 0.80),
    "Bookstore": (5, 100, 0.90),
    "Clothing": (20, 600, 0.70),
    "Convenience Store": (2, 80, 0.95),
    "Travel Agency": (200, 5000, 0.20),
    "Digital Services": (5, 200, 0.85),
    "Cryptocurrency Exchange": (50, 5000, 0.30),
}


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
            %(merchant_tags)s,
            %(device_id)s
        );
        """,
        txn
    )