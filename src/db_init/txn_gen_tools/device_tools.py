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

# import uuid
# import hashlib

# def gen_new_device(devices, timestamp, db):
#     """
#     Generate a list of random devices.
#     """
#     while True:
#         device_id = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()

#         check_device = db.query(
#             """
#             SELECT * FROM device_sessions " \
#             WHERE device_id = %(device_id)s
#             """,  {"device_id": device_id})
#         if not check_device:
            
#             db.execute(
#                 """
#                 INSERT INTO device_sessions (
#                     id, 
#                     entity_id, 
#                     device_id, 
#                     session_start_time, 
#                     session_end_time) 
#                 VALUES (%(device_id)s)
#                 """, {
#                     "device_id": device_id}
#             )
#             break
    
#     return device_id