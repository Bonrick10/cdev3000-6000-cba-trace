""" Checks the transaction against the current rules in ruleset"""
from datetime import datetime, timedelta
from geopy.distance import geodesic

from label import Label
from rules.rule_enum import RuleEnum

IMPOSSIBLE_TRAVEL_THRESHOLD = 500  # Note that this is km/hr
NEW_PAYEE_UNUSUAL_THRESHOLD = 10000
FRESH_ACCOUNT_NUM_TRANSACTIONS_THRESHOLD = 5
FRESH_ACCOUNT_AGE_THRESHOLD_DAYS = 15

def check_rules(transaction, surrounding_info):
    """ Checks the transaction against the current rules in ruleset"""
    rule_violations = []
    unseen_device_retval = check_unseen_device(transaction, surrounding_info)

    # Check suspcious rules first
    for function in [
        check_impossible_travel,
        check_merchant_type_suspicious_range
    ]:
        retval = function(transaction, surrounding_info)
        if retval is not None:
            rule_violations.append(retval)

    if len(rule_violations) > 0:
        print(f"Ruleset Label: Suspicious. Rule violation(s): {rule_violations}")
        return (Label.SUSPICIOUS, unseen_device_retval is not None)

    # Then check unusual rules
    if unseen_device_retval is not None:
        rule_violations.append(unseen_device_retval)

    for function in [
        check_exceed_7d_total,
        check_large_amount_to_new_payee,
        check_merchant_type_unusual_range
    ]:
        retval = function(transaction, surrounding_info)
        if retval is not None:
            rule_violations.append(retval)

    if len(rule_violations) > 0:
        print(f"Ruleset Label: Unusual. Rule violation(s): {rule_violations}")
        return (Label.UNUSUAL, unseen_device_retval is not None)

    print("Ruleset Label: Legitimate.")
    return (Label.LEGITIMATE, unseen_device_retval is not None)

def check_unseen_device(transaction, surrounding_info):
    """
    1. Transaction made from a previously unseen device associated with the customer -> unusual
    """
    if is_fresh_account(transaction, surrounding_info):
        # Skip check for fresh accounts
        return None
    return RuleEnum.UNSEEN_DEVICE if not surrounding_info["device_seen_before"] else None

def check_exceed_7d_total(transaction, surrounding_info):
    """ 2. 24 hour spending exceeds customer's cumulative 7 day total -> unusual """
    if is_fresh_account(transaction, surrounding_info):
        # Skip check for fresh accounts
        return None

    return (RuleEnum.EXCEED_7D_TOTAL if
            (transaction["amount"] + surrounding_info["24_hour_spending"]
            > surrounding_info["7_day_spending"])
            else None)

def check_impossible_travel(transaction, surrounding_info):
    """ 3. Two transactions made more than 500km apart per hour -> suspicious """
    if surrounding_info["last_transaction_time"] is None:
        # If no last transaction, skip this check
        return None
    distance = geodesic(
        (
            surrounding_info["last_transaction_latitude"],
            surrounding_info["last_transaction_longitude"]
        ),
        (transaction["sender_latitude"], transaction["sender_longitude"]),
    ).km
    delta_time_hours = (
        datetime.fromisoformat(transaction["transaction_time"])
        - datetime.fromisoformat(surrounding_info["last_transaction_time"])
        ).total_seconds() / 3600

    # Should not happen but avoid division by zero
    if delta_time_hours == 0:
        return None
    return (RuleEnum.IMPOSSIBLE_TRAVEL
            if distance / delta_time_hours > IMPOSSIBLE_TRAVEL_THRESHOLD
            else None)


def check_large_amount_to_new_payee(transaction, surrounding_info):
    """ 4. Transactions in excess of $10 000 to new payees -> unusual """
    if is_fresh_account(transaction, surrounding_info):
        # Skip check for fresh accounts
        return None

    return (RuleEnum.LARGE_AMOUNT_NEW_PAYEE
        if surrounding_info["is_new_payee"] and transaction["amount"] > NEW_PAYEE_UNUSUAL_THRESHOLD
        else None )


def check_merchant_type_unusual_range(transaction, surrounding_info):
    """5. Transactions outside of normal range for merchant type -> unusual"""
    # Note that lower and upper thresholds may be NULL
    return (RuleEnum.MERCHANT_TYPE_UNUSUAL_RANGE
        if (
            (
                surrounding_info["usual_threshold_lower"]
                and transaction["amount"] < surrounding_info["usual_threshold_lower"]
            )
            or
            (
                surrounding_info["usual_threshold_upper"]
                and transaction["amount"] > surrounding_info["usual_threshold_upper"]
            )
        ) else None )

def check_merchant_type_suspicious_range(transaction, surrounding_info):
    """6. Transactions far exceed normal range for merchant type -> suspicious"""
    # Note that lower and upper thresholds may be NULL
    return (RuleEnum.MERCHANT_TYPE_SUSPICIOUS_RANGE
        if (
            (
                surrounding_info["suspicious_threshold_lower"]
                and transaction["amount"] < surrounding_info["suspicious_threshold_lower"]
            )
            or
            (
                surrounding_info["suspicious_threshold_upper"]
                and transaction["amount"] > surrounding_info["suspicious_threshold_upper"]
            )
        ) else None)

def is_fresh_account(transaction, surrounding_info):
    """
        Checks whether an account is considered a new account by checking whether
            1. Number of transactions < FRESH_ACCOUNT_NUM_TRANSACTIONS_THRESHOLD
            2. First transaction >= current time - FRESH_ACCOUNT_AGE_THRESHOLD_DAYS
        If it is a fresh account, will bypass some of the rules
    """
    if surrounding_info["first_transaction_time"] is None:
        return True
    transaction_time = datetime.fromisoformat(transaction["transaction_time"])
    first_transaction_time = datetime.fromisoformat(surrounding_info["first_transaction_time"])
    return (
        surrounding_info["num_transactions"] < FRESH_ACCOUNT_NUM_TRANSACTIONS_THRESHOLD
        # Be advised this is day as in 24 hour not by calendar day at midnight
        or first_transaction_time >= (
            transaction_time - timedelta(days=FRESH_ACCOUNT_AGE_THRESHOLD_DAYS)
        )
    )
