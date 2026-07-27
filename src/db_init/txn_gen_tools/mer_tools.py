import random

def choose_any_merchant_receiver(merchants, merchant_tags):
    merchant = random.choice(merchants)
    return (merchant["bsb"], merchant["account_number"], merchant["merchant_tag"], get_merchant_legitimate_amount(merchant_tags[merchant["merchant_tag"]]))

def choose_known_merchant_receiver(seed_acc_txns, merchants, merchant_tags):
    past_merchant_txns = [
        transaction for transaction in seed_acc_txns 
        if transaction["merchant_tags"] is not None
    ]

    if len(past_merchant_txns) == 0: 
        # fallback since potentially all the young transactions went to p2p (forced unusual)
        return choose_any_merchant_receiver(merchants, merchant_tags)

    merchant = random.choice(past_merchant_txns)
    return (merchant["bsb"], merchant["account_number"], merchant["merchant_tag"], get_merchant_legitimate_amount(merchant_tags[merchant["merchant_tag"]]))

def get_merchant_legitimate_amount(merchant_tag):
    # Convert Decimal to float for random.uniform
    low = float(merchant_tag["usual_threshold_lower"])
    high = float(merchant_tag["usual_threshold_upper"])
    return round(random.uniform(low, high), 2)
