import random

def choose_any_merchant_receiver(seed_account, merchants, merchant_tags):
    merchant = random.choice(merchants)
    return (merchant["bsb"], merchant["account_number"], merchant["merchant_tag"], get_merchant_legitimate_amount(merchant["merchant_tag"], merchant_tags))

def choose_known_merchant_receiver(seed_account, seed_acc_txns, merchants, merchant_tags):
    past_merchant_txns = [
        t for t in seed_acc_txns 
        if t.get("is_merchant")
    ]

    if len(past_merchant_txns) == 0: 
        # fallback since potentially all the young transactions went to p2p
        return choose_any_merchant_receiver(seed_account, merchants, merchant_tags)

    merchant = random.choice(past_merchant_txns)
    return (merchant["bsb"], merchant["account_number"], merchant["merchant_tag"], get_merchant_legitimate_amount(merchant["merchant_tag"], merchant_tags))

def get_merchant_legitimate_amount(merchant_tag_id, merchant_tags):
    merchant_tag = next((m for m in merchant_tags if m["id"] == merchant_tag_id), None)
    # Convert Decimal to float for random.uniform
    low = float(merchant_tag["usual_threshold_lower"])
    high = float(merchant_tag["usual_threshold_upper"])
    return round(random.uniform(low, high), 2)