"""
Fraud detection system that runs when a new transaction is entered, the process goes as follows
1. Checks the transaction against the ruleset
2. Uses the large model to determine a score, and checks if that score exceeds a threshold
3. Uses the small model to determine whether the transaction falls in a cluster that
    has many cases of fraud
If any point fails then the transaction is blocked, otherwise it is allowed to go through
"""

import collections
import json
from pathlib import Path

from src.label import Label
from src.rules.rules import check_rules
from src.utils.db import NeonDB

BASE_DIR = Path(__file__).resolve().parent
SQL_DIR = BASE_DIR / "sql"

MODEL_UNUSUAL_THRESHOLD = 0.7
MODEL_SUSPICIOUS_THRESHOLD = 0.9
# True to just test what it would predict and not insert data
# False to insert data as well
DRYRUN_FLAG = True

RECURRING_TXN_AGE_THRESHOLD_DAYS = 7
RECURRING_TXN_AMOUNT_VARIANCE = 5.0
RECURRING_TXN_TIME_VARIANCE_MINUTES = 30


# For now this will just read in the new transaction from a json file
# Ideally for the final demo the user would be able to enter a transaction through the frontend UI
# Which would send the transaction in a JSON format to the backend which can then call this function
def read_transaction(filename):
    """Reads in transaction from json file"""
    with open(filename, "r", encoding="utf-8") as file:
        contents = json.load(file)
        return contents


def process_transaction(transaction):
    """
    Fraud detection pipeline that determines whether a transaction is fraud or not
    Using ruleset, large and small models
    """
    db = NeonDB()
    # convert non entries into None - especially for merchant_tags which may not be provided
    query_params = collections.defaultdict(lambda: None, transaction)
    query_params.update(
        {
            "RECURRING_TXN_AGE_THRESHOLD_DAYS": RECURRING_TXN_AGE_THRESHOLD_DAYS,
            "RECURRING_TXN_AMOUNT_VARIANCE": RECURRING_TXN_AMOUNT_VARIANCE,
            "RECURRING_TXN_TIME_VARIANCE_MINUTES": RECURRING_TXN_TIME_VARIANCE_MINUTES,
        }
    )
    surrounding_info = db.query(
        db.read_sql_file(SQL_DIR / "get_surrounding_info.sql"), query_params
    )[0]["json_build_object"]
    print(surrounding_info)

    ruleset_label, is_unseen_device = check_rules(transaction, surrounding_info)
    if ruleset_label == Label.SUSPICIOUS:
        insert_db_entries(db, transaction, surrounding_info, Label.SUSPICIOUS, is_unseen_device)
        return Label.SUSPICIOUS

    # Call Large Model

    # Call Small Model

    # TODO: Set to most severe of ruleset, large and small model verdict
    final_label = ruleset_label
    insert_db_entries(db, transaction, surrounding_info, final_label, is_unseen_device)
    print(f"Final label: {final_label}")
    return final_label


def insert_db_entries(db, transaction, surrounding_info, label, is_unseen_device):
    """Insert appropriate db entries for new transaction if not a dryrun"""
    if DRYRUN_FLAG:
        return

    # TODO: Insert transaction incl fraud ones

    if label != Label.SUSPICIOUS:
        # TODO: Move funds from sender to receiver
        pass

    if is_unseen_device:
        # If device and entity combination not seen before, add a new session for this combination
        # TODO: Also add session if combination seen before but expired
        db.execute(
            """
            INSERT INTO 
                device_sessions (entity_id, device_id, session_start_time, session_end_time)
            VALUES (%s, %s, %s, NULL)
        """,
            [
                surrounding_info["entity_id"],
                transaction["device_id"],
                transaction["transaction_time"],
            ],
        )


process_transaction(read_transaction("src/test_new_transaction.json"))
