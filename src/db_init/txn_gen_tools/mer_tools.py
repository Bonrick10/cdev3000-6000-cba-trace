import random

def choose_new_payee(seed_acc_txns, merchants, merchant_tags):
    past_merchant_txns = [
        transaction for transaction in seed_acc_txns 
        if transaction["merchant_tags"] is not None
    ]
    
    merchant_keys = {
        (txn["receiver_bsb"], txn["receiver_account_number"])
        for txn in past_merchant_txns
    }

    unknown_merchants = [
        merchant for merchant in merchants
        if (merchant["bsb"], merchant["account_number"]) not in merchant_keys
    ]
    
    merchant = random.choice(unknown_merchants)
    amount = get_merchant_legitimate_amount(merchant_tags[merchant["merchant_tag"]])

    return (
        merchant["bsb"], 
        merchant["account_number"], 
        merchant["merchant_tag"], 
        amount)

def choose_any_merchant_receiver(merchants, merchant_tags):
    merchant = random.choice(merchants)
    amount = get_merchant_legitimate_amount(merchant_tags[merchant["merchant_tag"]])
    return (
        merchant["bsb"], 
        merchant["account_number"], 
        merchant["merchant_tag"], 
        amount)

def choose_known_merchant_receiver(seed_acc_txns, merchants, merchant_tags):
    past_merchant_txns = [
        transaction for transaction in seed_acc_txns 
        if transaction["merchant_tags"] is not None
    ]

    if len(past_merchant_txns) == 0: 
        # fallback since potentially all the young transactions went to p2p (forced unusual)
        return choose_any_merchant_receiver(merchants, merchant_tags)

    merchant_keys = {
        (txn["receiver_bsb"], txn["receiver_account_number"])
        for txn in past_merchant_txns
    }

    known_merchants = [
        merchant for merchant in merchants
        if (merchant["bsb"], merchant["account_number"]) in merchant_keys
    ]
    merchant = random.choice(known_merchants)
    amount = get_merchant_legitimate_amount(merchant_tags[merchant["merchant_tag"]])

    return (
        merchant["bsb"], 
        merchant["account_number"], 
        merchant["merchant_tag"], 
        amount)

def get_merchant_legitimate_amount(merchant_tag):
    # Convert Decimal to float for random.uniform
    low = float(merchant_tag["usual_threshold_lower"])
    high = float(merchant_tag["usual_threshold_upper"])
    return round(random.uniform(low, high), 2)

def get_merchant_data(merchant_tag, merchant_tags):
    merchant_data = merchant_tags[merchant_tag]
    
    sus_lower = merchant_data["suspicious_threshold_lower"]
    usual_lower = merchant_data["usual_threshold_lower"]
    usual_upper = merchant_data["usual_threshold_upper"]
    sus_upper = merchant_data["suspicious_threshold_upper"]
    return sus_lower, usual_lower, usual_upper, sus_upper
