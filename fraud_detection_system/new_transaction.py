""" 
    Fraud detection system that runs when a new transaction is entered, the process goes as follows
    1. Checks the transaction against the ruleset 
    2. Uses the large model to determine a score, and checks if that score exceeds a threshold 
    3. Uses the small model to determine whether the transaction falls in a cluster that has many cases of fraud
    If any point fails then the transaction is blocked, otherwise it is allowed to go through
"""
import json 

# For now this will just read in the new transaction from a json file 
# Ideally for the ifnal demo the user would be able to enter a transaction through the frontend UI 
# Which would send the transaction in a JSON format to the backend which can then call this function 
def read_transaction(filename): 
    with open(filename, "r") as file: 
        contents = json.load(file)
        print(contents)

def process_transaction():
    pass

def check_rules(): 
    pass
    
read_transaction("fraud_detection_system/test_new_transaction.json")