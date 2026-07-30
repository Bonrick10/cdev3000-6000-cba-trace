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
from utils.db import NeonDB
from db_init.txn_gen_tools import mer_tools, p2p_tools, loc_tools, device_tools 

THRESHOLD_LOW_TXNS = 5
THRESHOLD_YOUNG_ACC = timedelta(days=15)
SUSPICIOUS_TXN_RATE = 0.004
UNUSUAL_TXN_RATE = 0.010
RECEIVER_MERCHANT_RATE = 0.80
LABELS = [
    'confirmed_legitimate', 
    'legitimate', 
    'unusual', 
    'suspicious', 
    'confirmed_fraudulent', 
    'rule_violation'
    ]

import random
from datetime import timedelta

def gen_timeline(base_time, end_time):
    # step = timedelta(minutes=5)
    # step = timedelta(hours=2)
    step = timedelta(hours=12)
    noise_seconds = 90

    total_seconds = (end_time - base_time).total_seconds()
    num_steps = int(total_seconds // step.total_seconds())

    txn_times = []
    for g in range(num_steps + 1):
        t = base_time + g * step

        # Add noise: random offset between -noise_seconds and +noise_seconds
        offset = timedelta(seconds=random.randint(-noise_seconds, noise_seconds))
        noisy_t = t + offset

        # Ensure timestamps never go backwards
        if txn_times and noisy_t <= txn_times[-1]:
            noisy_t = txn_times[-1] + timedelta(seconds=1)

        txn_times.append(noisy_t)

    return txn_times


def gen_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, device_sessions, new_txn_time, db):
    """
    Generate a transaction based on the seed account and its history.
    """
    r = random.random()
    
    if r < SUSPICIOUS_TXN_RATE:
        return gen_sus_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, device_sessions, new_txn_time, db)
    elif r < SUSPICIOUS_TXN_RATE + UNUSUAL_TXN_RATE:
        return gen_unusual_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, device_sessions, new_txn_time, db)
    else:
        return gen_legit_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, device_sessions, new_txn_time, db)

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
        entity_id = seed_account["entity_id"]
        device_id = device_tools.gen_new_device_id(entity_id, new_txn_time, db)
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
        entity_id = seed_account["entity_id"]
        device_id = device_tools.choose_known_device(entity_id, seed_acc_txns, new_txn_time, db)
    
    return [{
        "sender_bsb": seed_account["bsb"],
        "sender_account_number": seed_account["account_number"],
        "receiver_bsb": receiver_bsb,
        "receiver_account_number": receiver_acc,
        "amount": amount,
        "transaction_time": new_txn_time,
        "sender_latitude": lat,
        "sender_longitude": lon,
        "label": LABELS[1],
        "merchant_tags": merchant_tag,
        "device_id": device_id
    }]

def gen_unusual_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, device_sessions, new_txn_time, db):
    """
    Generate a mildly abnormal transaction.
    Behaviour:
    - new device 
    - new payee 
    - slightly large amount to p2p
    - unusual merchant payment range
    - unusual location (work or small travel)
    - unusual time-of-day (early morning or late night)
    """

    # 50% chance of new payee
    if random.random() < 0.5:
        receiver_bsb, receiver_acc, merchant_tag, amount = mer_tools.choose_new_payee(
                seed_acc_txns=seed_acc_txns,
                merchants=merchants,
                merchant_tags=merchant_tags
        )
    else:
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
                accounts=accounts
            )
            merchant_tag = None

    # 30% chance of unusual location
    if random.random() < 0.3:
        lat, lon = loc_tools.gen_rand_loc()
    else:
        lat, lon = loc_tools.gen_near_loc(seed_acc_txns)

    # 20% chance of unseen device
    if random.random() < 0.2:
        entity_id = seed_account["entity_id"]
        device_id = device_tools.gen_new_device_id(entity_id, new_txn_time, db)
    else:
        entity_id = seed_account["entity_id"]
        device_id = device_tools.choose_known_device(entity_id, seed_acc_txns, new_txn_time, db)

    return [{
       "sender_bsb": seed_account["bsb"],
        "sender_account_number": seed_account["account_number"],
        "receiver_bsb": receiver_bsb,
        "receiver_account_number": receiver_acc,
        "amount": amount,
        "transaction_time": new_txn_time,
        "sender_latitude": lat,
        "sender_longitude": lon,
        "label": LABELS[2],
        "merchant_tags": merchant_tag,
        "device_id": device_id
    }]

def gen_sus_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, device_sessions, new_txn_time, db):
    """
    Generate a rule-breaking suspicious transaction.
    Behaviour:
    - impossible travel (far location)
    - very large amount
    - unseen device
    - suspicious merchant category
    - unusual time-of-day
    """

    if random.random() > 0.3:
        # impossible travel: generate two locations far apart from each other and two transactions within a short time window
        return gen_impossible_travel_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, device_sessions, new_txn_time, db)
    else:
        if random.random() > 0.6:
            receiver_bsb, receiver_acc, merchant_tag, amount = mer_tools.choose_any_merchant_receiver(
                merchants=merchants,
                merchant_tags=merchant_tags
            )
        else:
            receiver_bsb, receiver_acc, amount = p2p_tools.choose_any_p2p_receiver(
                seed_acc_txns=seed_acc_txns,
                accounts=accounts
            )
            merchant_tag = None

        # force extreme amount
        if merchant_tag is not None and random.random() > 0.5:
            min_amt, max_amt, _ = mer_tools.get_merchant_data(merchant_tag)
            if random.random() > 0.5:
                amount = round(random.uniform(min_amt * 0.5, min_amt), 2)
            else:
                amount = round(random.uniform(max_amt, max_amt * 1.5), 2)

        # unseen device
        if random.random() > 0.5:
            entity_id = seed_account["entity_id"]
            device_id = device_tools.gen_new_device_id(entity_id, new_txn_time, db)
        else:
            entity_id = seed_account["entity_id"]
            device_id = device_tools.choose_known_device(entity_id, seed_acc_txns, new_txn_time, db)

        lat, lon = loc_tools.gen_near_loc(seed_acc_txns)

    return [{
        "sender_bsb": seed_account["bsb"],
        "sender_account_number": seed_account["account_number"],
        "receiver_bsb": receiver_bsb,
        "receiver_account_number": receiver_acc,
        "amount": amount,
        "transaction_time": new_txn_time,
        "sender_latitude": lat,
        "sender_longitude": lon,
        "label": LABELS[5],
        "merchant_tags": merchant_tag,
        "device_id": device_id
    }]

def remove_sender_from_account_list(sender_acc, account_list): 
    return list(filter(lambda acc: (acc["bsb"] != sender_acc["bsb"]) or (acc["account_number"] != sender_acc["account_number"]), account_list))

def gen_impossible_travel_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, device_sessions, new_txn_time, db):
    """
    Generate a transaction that simulates impossible travel.
    Behaviour:
    - two transactions in quick succession with locations far apart
    - unseen device
    - suspicious merchant category
    """

    # Generate first transaction normally
    first_txn = gen_legit_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, device_sessions, new_txn_time, db)

    # Generate any second transaction
    second_txn_time = new_txn_time + timedelta(minutes=random.randint(1, 10))
    if random.random() > 0.7:
        second_txn = gen_legit_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, device_sessions, second_txn_time, db)
    else:
        second_txn = gen_unusual_txn(seed_account, seed_acc_txns, accounts, merchants, merchant_tags, device_sessions, second_txn_time, db)
    
    lat, lon = loc_tools.gen_far_loc(first_txn["sender_latitude"], first_txn["sender_longitude"])
    
    second_txn = {
        "sender_bsb": seed_account["bsb"],
        "sender_account_number": seed_account["account_number"],
        "receiver_bsb": second_txn["receiver_bsb"],
        "receiver_account_number": second_txn["receiver_account_number"],
        "amount": second_txn["amount"],
        "transaction_time": second_txn_time,
        "sender_latitude": lat,
        "sender_longitude": lon,
        "label": LABELS[5],
        "merchant_tags": second_txn["merchant_tags"],
        "device_id": second_txn["device_id"]
    }

    return [first_txn, second_txn]
