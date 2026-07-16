""" 
    Fraud detection system that runs when a new transaction is entered, the process goes as follows
    1. Checks the transaction against the ruleset 
    2. Uses the large model to determine a score, and checks if that score exceeds a threshold 
    3. Uses the small model to determine whether the transaction falls in a cluster that 
        has many cases of fraud
    If any point fails then the transaction is blocked, otherwise it is allowed to go through
"""
import sys
sys.path.insert(0, ".")  # add Folder_2 path to search list
import json
from label import Label
from db import get_transaction_surrounding_info
from geopy.distance import geodesic

MODEL_UNUSUAL_THRESHOLD = 0.7
MODEL_SUSPICIOUS_THRESHOLD = 0.9
# True to just test what it would predict and not insert data 
# False to insert data as well 
DRYRUN_FLAG = True 

# For now this will just read in the new transaction from a json file
# Ideally for the ifnal demo the user would be able to enter a transaction through the frontend UI
# Which would send the transaction in a JSON format to the backend which can then call this function
def read_transaction(filename):
    with open(filename, "r") as file:
        contents = json.load(file)
        return contents

def process_transaction(transaction):
    surrounding_info = get_transaction_surrounding_info(transaction)
    print(surrounding_info)

    ruleset_result = check_rules(transaction, surrounding_info)

def check_rules(transaction, surrounding_info):
    pass
    # 1. Transaction made from a previously unseen device associated with the customer -> unusual 
    # 2. Total spending exceeds customer's weekly average within a single day -> unusual
    
    # 3. Two transactions made more than 500km apart per hour -> suspicious
    distance = geodesic((surrounding_info["last_transaction_lattitude"], surrounding_info["last_transaction_longitude"]),(transaction["sender_latitude"], transaction["sender_longitude"])).km
    print(distance)
    # 4. Transactions in excess of $10 000 to new payees -> unusual 
    # 6. Transactions far exceed normal range for merchant type -> suspicious  
    # 5. Transactions outside of normal range for merchant type -> unusual  

process_transaction(read_transaction("fraud_detection_system/test_new_transaction.json"))
