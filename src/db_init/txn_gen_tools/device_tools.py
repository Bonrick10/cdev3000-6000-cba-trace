import random

def generate_random_device_id() -> str:
    """
    Generate a random 64-character hex device ID.

    Returns:
        A device ID string.
    """
    return secrets.token_hex(32)

# TODO: Choose session that has start time before and end time after cur_time
# TODO: These two are stubbed and incomplete for now  
def choose_any_device(devices):
    # For now this returns any existing device_id even if not related to account entity 
    return random.choice(devices)["device_id"]

def choose_known_device(seed_acc_txns, devices):
    known_devices = [txn["device_id"] for txn in seed_acc_txns]

    if len(known_devices) == 0: 
        # TODO: Figure out why sometimes empty since should have inserted some during young stage, fallback for now 
        return choose_any_device(seed_account, devices)

    return random.choice(known_devices["device_id"])