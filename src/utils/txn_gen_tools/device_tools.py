import random

def choose_any_device(seed_account, devices):
    return random.choice(devices)["device_id"]

def choose_known_device(seed_account, seed_acc_txns, devices):
    known_devices = [txn["device_id"] for txn in seed_acc_txns]

    if len(known_devices) == 0: 
        # TODO: Figure out why sometimes empty, fallback for now 
        return choose_any_device(seed_account, devices)

    return random.choice(known_devices["device_id"])
