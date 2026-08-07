INSERT INTO device_sessions (
    entity_id,
    device_id,
    session_start_time,
    session_end_time
) VALUES (
    %(entity_id)s,
    %(device_id)s,
    %(transaction_time)s,
    NULL
);
