INSERT INTO transactions (
    sender_bsb,
    sender_account_number,
    receiver_bsb,
    receiver_account_number,
    amount,
    transaction_time,
    sender_latitude,
    sender_longitude,
    label,
    merchant_tags,
    device_id
) VALUES (
    %(sender_bsb)s,
    %(sender_account_number)s,
    %(receiver_bsb)s,
    %(receiver_account_number)s,
    %(amount)s,
    %(transaction_time)s,
    %(sender_latitude)s,
    %(sender_longitude)s,
    %(label)s,
    %(merchant_tags)s,
    %(device_id)s
)
RETURNING id;
