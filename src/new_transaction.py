""" 
    Fraud detection system that runs when a new transaction is entered, the process goes as follows
    1. Checks the transaction against the ruleset 
    2. Uses the large model to determine a score, and checks if that score exceeds a threshold 
    3. Uses the small model to determine whether the transaction falls in a cluster that 
        has many cases of fraud
    If any point fails then the transaction is blocked, otherwise it is allowed to go through
"""
import json
from label import Label
from rules.rules import check_rules

MODEL_UNUSUAL_THRESHOLD = 0.7
MODEL_SUSPICIOUS_THRESHOLD = 0.9
# True to just test what it would predict and not insert data
# False to insert data as well
DRYRUN_FLAG = True

# For now this will just read in the new transaction from a json file
# Ideally for the final demo the user would be able to enter a transaction through the frontend UI
# Which would send the transaction in a JSON format to the backend which can then call this function
def read_transaction(filename):
    """ Reads in transaction from json file """
    with open(filename, "r", encoding="utf-8") as file:
        contents = json.load(file, encoding="utf-8")
        return contents

def process_transaction(transaction):
    """
        Fraud detection pipeline that determines whether a transaction is fraud or not
        Using ruleset, large and small models
    """
    ruleset_result = check_rules(transaction, DRYRUN_FLAG)
    if ruleset_result == Label.SUSPICIOUS:
        return Label.SUSPICIOUS

    # Call Large Model

    # Call Small Model

    if ruleset_result == Label.LEGITIMATE and not DRYRUN_FLAG:
        # Insert new transaction into db
        pass
    return ruleset_result

process_transaction(read_transaction("src/test_new_transaction.json"))
