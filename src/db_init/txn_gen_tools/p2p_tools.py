import random

def choose_any_p2p_receiver(seed_account, accounts):
    receiver = random.choice(accounts)
    # Below the 10k unusual range TODO: Fix to proper amount
    return (receiver["bsb"], receiver["account_number"], random.uniform(0.0, 9999))

def choose_known_p2p_receiver(seed_account, seed_acc_txns, accounts):
    past_p2p_txns = [
        t for t in seed_acc_txns
        if transaction["merchant_tags"] is None
    ]

    if len(past_p2p_txns) == 0: 
        # fallback since potentially all the young transactions went to merchant
        return choose_any_p2p_receiver(seed_account, accounts)

    chosen_txn = random.choice(past_p2p_txns)

    # Thanks AI 
    # Base new amount near their usual transfer size (±25%)
    prev_amt = float(chosen_txn.get("amount", 50.0))
    min_amt = max(5.0, prev_amt * 0.75)
    max_amt = prev_amt * 1.25
    amount = round(random.uniform(min_amt, max_amt), 2)

    return (chosen_txn["receiver_bsb"], chosen_txn["receiver_account_number"], amount)