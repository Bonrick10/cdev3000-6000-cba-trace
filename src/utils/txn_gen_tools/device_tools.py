
import uuid
import hashlib

def gen_new_device(devices, timestamp, db):
    """
    Generate a list of random devices.
    """
    while True:
        device_id = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()

        check_device = db.query(
            """
            SELECT * FROM device_sessions " \
            WHERE device_id = %(device_id)s
            """,  {"device_id": device_id})
        if not check_device:
            
            db.execute(
                """
                INSERT INTO device_sessions (
                    id, 
                    entity_id, 
                    device_id, 
                    session_start_time, 
                    session_end_time) 
                VALUES (%(device_id)s)
                """, {
                    "device_id": device_id}
            )
            break
    
    return device_id