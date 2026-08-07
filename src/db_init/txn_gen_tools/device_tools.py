import random
import secrets
from datetime import datetime, timedelta, timezone

SESSION_DURATION = timedelta(hours=1)
END_TIME = datetime(
    2026, 6, 30, 23, 59, 59, tzinfo=timezone.utc
)  # 2026-06-30 23:59:59+00


def gen_new_device_id(entity_id, timestamp, db) -> str:
    """Generate a random 64-character hex device ID and generates a new session with it

    Returns:
        A device ID string.

    """
    device_id = secrets.token_hex(32)
    gen_device_session(device_id, timestamp, entity_id, db)

    return device_id


# Why would this happen? Should it be a new rule?
# def choose_any_device(devices):
#     # For now this returns any existing device_id even if not related to account entity
#     return random.choice(devices)["device_id"]


def choose_known_device(entity_id, seed_acc_txns, timestamp, db):
    """Chooses a known device and generates a new session.

    Returns:
        A device ID string.

    """
    known_devices = {txn["device_id"] for txn in seed_acc_txns}

    if len(known_devices) == 0:
        # Fresh account, no known devices, generate a new device (forced to be unusual)
        return gen_new_device_id(entity_id, timestamp, db)

    device_id = random.choice(list(known_devices))
    gen_device_session(device_id, timestamp, entity_id, db)

    return device_id


def gen_device_session(device_id, session_start_time, entity_id, db):
    """Generate a device session for a given device ID and session_start_time."""
    # This emulates a logout
    noisy_session_duration = SESSION_DURATION + timedelta(minutes=random.randint(-5, 5))
    session_end_time = session_start_time + noisy_session_duration

    # The static NOW time would represent active sessions with a Null end time
    if session_end_time > END_TIME:
        session_end_time = None

    db.execute(
        """
        INSERT INTO device_sessions (
            entity_id,
            device_id,
            session_start_time,
            session_end_time
        ) VALUES (%(entity_id)s, %(device_id)s, %(session_start_time)s, %(session_end_time)s)
        """,
        {
            "entity_id": entity_id,
            "device_id": device_id,
            "session_start_time": session_start_time,
            "session_end_time": session_end_time,
        },
    )
