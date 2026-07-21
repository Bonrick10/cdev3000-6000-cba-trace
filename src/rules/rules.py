""" Checks the transaction against the current rules in ruleset"""
import collections
from pathlib import Path
import datetime
from geopy.distance import geodesic
from utils.db import NeonDB
from label import Label

BASE_DIR = Path(__file__).resolve().parent
SQL_DIR = BASE_DIR / "sql"

IMPOSSIBLE_TRAVEL_THRESHOLD = 500 # Note that this is km/hr
NEW_PAYEE_UNUSUAL_THRESHOLD = 10000

def check_rules(transaction, dryrun_flag = True):
    """ Checks the transaction against the current rules in ruleset"""
    db = NeonDB()
    print(transaction)
    # convert non entries into None - especially for merchant_tags which may not be provided
    surrounding_info = db.query(
        db.read_sql_file(SQL_DIR / "get_surrounding_info.sql"),
        collections.defaultdict(lambda: None, transaction
        ))[0]["json_build_object"]
    print(surrounding_info)
 
    # Check Suspicious rules first and Instant Exit if fails
    if (
        check_impossible_travel(transaction, surrounding_info)
        or check_merchant_type_suspicious_range(transaction, surrounding_info)
        ):
        return Label.SUSPICIOUS

    # Then check unusual rules, but don't instant fail
    return (Label.UNUSUAL
        if (
            check_unseen_device(transaction, surrounding_info, db, dryrun_flag)
            or check_exceed_weekly_total(transaction, surrounding_info)
            or check_large_amount_to_new_payee(transaction, surrounding_info)
            or check_merchant_type_suspicious_range(transaction, surrounding_info)
        ) else Label.LEGITIMATE)

def check_unseen_device(transaction, surrounding_info, db, dryrun_flag = True):
    """ 
    1. Transaction made from a previously unseen device associated with the customer -> unusual
    """
    if not surrounding_info["device_seen_before"] and not dryrun_flag:
        # If device and entity combination not seen before, add a new session for this combination
        # TODO: Also add session if combination seen before but expired
        db.execute("""
            INSERT INTO 
                device_sessions (entity_id, device_id, session_start_time, session_end_time)
            VALUES (%s, %s, %s, NULL)
        """, [
            surrounding_info["entity_id"],
            transaction["device_id"],
            transaction["transaction_time"]
        ])
    return not surrounding_info["device_seen_before"]

def check_exceed_weekly_total(transaction, surrounding_info):
    """ 2. 24 hour spending exceeds customer's cumulative 7 day total -> unusual """
    return (transaction["amount"] + surrounding_info["24_hour_spending"]
            > surrounding_info["7_day_spending"])

def check_impossible_travel(transaction, surrounding_info):
    """ 3. Two transactions made more than 500km apart per hour -> suspicious """
    # If no last transaction, skip this check
    if surrounding_info["last_transaction_time"] is None:
        return False
    distance = geodesic(
        (
            surrounding_info["last_transaction_lattitude"],
            surrounding_info["last_transaction_longitude"]
        ),
        (
            transaction["sender_latitude"],
            transaction["sender_longitude"]
        )
        ).km
    delta_time_hours = (
        datetime.datetime.fromisoformat(transaction["transaction_time"])
        - datetime.datetime.fromisoformat(surrounding_info["last_transaction_time"])
        ).total_seconds() / 3600

    # Should not happen but avoid division by zero
    if delta_time_hours == 0:
        return False
    return distance / delta_time_hours > IMPOSSIBLE_TRAVEL_THRESHOLD

def check_large_amount_to_new_payee(transaction, surrounding_info):
    """ 4. Transactions in excess of $10 000 to new payees -> unusual """
    return surrounding_info["is_new_payee"] and transaction["amount"] > NEW_PAYEE_UNUSUAL_THRESHOLD

def check_merchant_type_unusual_range(transaction, surrounding_info):
    """ 5. Transactions outside of normal range for merchant type -> unusual """
    # Note that lower and upper thresholds may be NULL
    return (
            (
                surrounding_info["usual_threshold_lower"]
                and transaction["amount"] < surrounding_info["usual_threshold_lower"]
            )
            or
            (
                surrounding_info["usual_threshold_upper"]
                and transaction["amount"] > surrounding_info["usual_threshold_upper"]
            )
        )

def check_merchant_type_suspicious_range(transaction, surrounding_info):
    """ 6. Transactions far exceed normal range for merchant type -> suspicious  """
    # Note that lower and upper thresholds may be NULL
    return (
            (
                surrounding_info["suspicious_threshold_lower"]
                and transaction["amount"] < surrounding_info["suspicious_threshold_lower"]
            )
            or
            (
                surrounding_info["suspicious_threshold_upper"]
                and transaction["amount"] > surrounding_info["suspicious_threshold_upper"]
            )
        )
