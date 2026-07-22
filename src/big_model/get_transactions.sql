SELECT
    t.id AS transaction_id,
    t.sender_bsb,
    t.sender_account_number,
    t.receiver_bsb,
    t.receiver_account_number,
    t.amount::numeric AS amount,
    t.transaction_time,
    t.sender_latitude::double precision AS sender_latitude,
    t.sender_longitude::double precision AS sender_longitude,
    t.label::text AS label,
    t.merchant_tags::text AS merchant_tag,
    TRIM(t.device_id) AS device_id

FROM transactions AS t

WHERE
    t.transaction_time >= %(start_time)s::timestamptz
    AND t.transaction_time < %(end_time)s::timestamptz

ORDER BY
    t.transaction_time ASC,
    t.id ASC;