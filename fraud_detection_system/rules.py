from geopy.distance import geodesic

def check_rules(transaction, surrounding_info):
    # Check Suspicious rules first and Instant Exit if fails
    check_impossible_travel(transaction, surrounding_info)
    check_merchant_type_suspicious_range(transaction, surrounding_info)
    
    # Then check unusual rules, but don't instant fail 
    check_unseen_device(transaction, surrounding_info)
    check_exceed_weekly_average(transaction, surrounding_info)
    check_large_amount_to_new_payee(transaction, surrounding_info)
    check_merchant_type_suspicious_range(transaction, surrounding_info)
    
    

def check_unseen_device(transaction, surrounding_info): 
    # 1. Transaction made from a previously unseen device associated with the customer -> unusual 
    pass

def check_exceed_weekly_average(transaction, surrounding_info):
    # 2. Total spending exceeds customer's cumulative 7 day total within 24 hours -> unusual
    pass 

def check_impossible_travel(transaction, surrounding_info): 
    # 3. Two transactions made more than 500km apart per hour -> suspicious
    distance = geodesic((surrounding_info["last_transaction_lattitude"], surrounding_info["last_transaction_longitude"]),(transaction["sender_latitude"], transaction["sender_longitude"])).km
    print(distance)

def check_large_amount_to_new_payee(transaction, surrounding_info):
    # 4. Transactions in excess of $10 000 to new payees -> unusual 
    pass

def check_merchant_type_unusual_range(transaction, surrounding_info): 
    # 5. Transactions outside of normal range for merchant type -> unusual  
    pass

def check_merchant_type_suspicious_range(transaction, surrounding_info): 
    # 6. Transactions far exceed normal range for merchant type -> suspicious  
    pass