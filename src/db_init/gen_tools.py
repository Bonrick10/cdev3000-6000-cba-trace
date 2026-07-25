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
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple, List, Any
from src.utils.db import NeonDB
from src.db_init.txn_gen_tools import mer_tools, p2p_tools, loc_tools, device_tools 

THRESHOLD_LOW_TXNS = 5
THRESHOLD_YOUNG_ACC = timedelta(days=15)
SUSPICIOUS_TXN_RATE = 0.004
UNUSUAL_TXN_RATE = 0.010
RECEIVER_MERCHANT_RATE = 0.80

def gen_timeline(base_time, end_time): 
    step = timedelta(minutes=5)

    total_seconds = (end_time - base_time).total_seconds()
    num_steps = int(total_seconds // step.total_seconds())

    # Just every 5 min for now, could add randomisation later
    txn_times = [base_time + g * step for g in range(num_steps + 1)] 
    return txn_times

def gen_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, device_sessions, new_txn_time, db):
    """
    Generate a transaction based on the seed account and its history.
    """
    r = random.random()

    return gen_legit_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, device_sessions, new_txn_time, db)
    # if r < SUSPICIOUS_TXN_RATE:
    #     return gen_sus_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, device_sessions, new_txn_time, db)
    # elif r < SUSPICIOUS_TXN_RATE + UNUSUAL_TXN_RATE:
    #     return gen_unusual_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, device_sessions, new_txn_time, db)
    # else:
    #     return gen_legit_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, device_sessions, new_txn_time, db)

def gen_legit_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, device_sessions, new_txn_time, db):
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

    first_txn_time = seed_acc_txns[0]["transaction_time"] if len(seed_acc_txns) > 0 else new_txn_time
    age = new_txn_time - first_txn_time
    # If young account, do any receiver 
    if len(seed_acc_txns) < THRESHOLD_LOW_TXNS or age < THRESHOLD_YOUNG_ACC:
        r = random.random()
        if r < RECEIVER_MERCHANT_RATE:
            receiver_bsb, receiver_acc, merchant_tag, amount = mer_tools.choose_any_merchant_receiver(
                merchants=merchants,
                merchant_tags=merchant_tags
        )
        else:
            receiver_bsb, receiver_acc, amount = p2p_tools.choose_any_p2p_receiver(
                seed_account=seed_account,
                accounts=remove_sender_from_account_list(seed_account, accounts)
            )
            merchant_tag = None
    
        lat, lon = loc_tools.gen_rand_loc()
        device_id = device_tools.choose_any_device(device_sessions)
    else:
        # Established account - do known receiver for legit
        r = random.random()
        if r < RECEIVER_MERCHANT_RATE:
            receiver_bsb, receiver_acc, merchant_tag, amount = mer_tools.choose_known_merchant_receiver(
                seed_acc_txns=seed_acc_txns,
                merchants=merchants,
                merchant_tags=merchant_tags
        )
        else:
            receiver_bsb, receiver_acc, amount = p2p_tools.choose_known_p2p_receiver(
                seed_account=seed_account,
                seed_acc_txns=seed_acc_txns,
                accounts=remove_sender_from_account_list(seed_account, accounts)
            )
            merchant_tag = None
        lat, lon = loc_tools.gen_near_loc(seed_acc_txns)
        device_id = device_tools.choose_known_device(seed_acc_txns, device_sessions)
    
    return {
        "sender_bsb": seed_account["bsb"],
        "sender_account_number": seed_account["account_number"],
        "receiver_bsb": receiver_bsb,
        "receiver_account_number": receiver_acc,
        "amount": amount,
        "transaction_time": new_txn_time,
        "sender_latitude": lat,
        "sender_longitude": lon,
        "label": "legitimate",
        "merchant_tags": merchant_tag,
        "device_id": device_id
    }

def gen_unusual_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, device_sessions, new_txn_time, db):
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
        if r < RECEIVER_MERCHANT_RATE:
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
        device_id = choose_device_from_seed(seed_account, device_sessions)

    return {
       "sender_bsb": seed_account["bsb"],
        "sender_account_number": seed_account["account_number"],
        "receiver_bsb": receiver_bsb,
        "receiver_account_number": receiver_acc,
        "amount": amount,
        "transaction_time": new_txn_time["txn_time"],
        "sender_latitude": lat,
        "sender_longitude": lon,
        "label": "suspicious",
        "merchant_tags": merchant_tag,
        "device_id": device_id
    }

def gen_sus_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, device_sessions, new_txn_time, db):
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
    new_txn_time = datetime.now().replace(
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
        "transaction_time": new_txn_time,
        "sender_latitude": lat,
        "sender_longitude": lon,
        "label": "suspicious",
        "merchant_tags": merchant_tag,
        "device_id": device_id
    }

def remove_sender_from_account_list(sender_acc, account_list): 
    return list(filter(lambda acc: (acc["bsb"] != sender_acc["bsb"]) or (acc["account_number"] != sender_acc["account_number"]), account_list))

# def generate_new_txn_time() -> datetime:
#     """
#     Generate a realistic new_txn_time for a transaction.

#     Returns:
#         A datetime object representing the transaction time.
#     """
#     weekday_bias = random.random() < 0.8
#     day_offset = random.randint(0, 4) if weekday_bias else random.randint(5, 6)

#     base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
#     date = base_date + timedelta(days=day_offset)

#     r2 = random.random()
#     if r2 < 0.80:
#         hour = random.randint(7, 21)
#     elif r2 < 0.95:
#         hour = random.randint(5, 6)
#     else:
#         hour = random.randint(22, 23)

#     minute = random.randint(0, 59)
#     second = random.randint(0, 59)

#     return date.replace(hour=hour, minute=minute, second=second)

