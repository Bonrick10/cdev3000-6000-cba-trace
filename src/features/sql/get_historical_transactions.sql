SELECT
    txn.id AS transaction_id,
    txn.sender_bsb,
    txn.sender_account_number,
    txn.receiver_bsb,
    txn.receiver_account_number,
    txn.amount::numeric AS amount,
    txn.transaction_time,
    txn.sender_latitude::double precision AS sender_latitude,
    txn.sender_longitude::double precision AS sender_longitude,
    -- Canonical builder contract calls ground truth "label"; it remains
    -- metadata/target and is never included in MODEL_FEATURES.
    txn.true_label::text AS label,
    txn.predicted_label::text AS observed_label,
    COALESCE(merchant.merchant_category, txn.merchant_tags::text, 'unknown') AS merchant_tag,
    TRIM(txn.device_id) AS device_id,
    CASE
        WHEN txn.predicted_label IN (
            'rule_approval',
            'rule_alert',
            'rule_violation'
        )
        THEN txn.predicted_label::text
        ELSE 'legitimate'
    END AS rules_label,
    CASE
        WHEN txn.predicted_label = 'rule_violation' THEN 'block'
        WHEN txn.predicted_label = 'rule_alert' THEN 'approve_and_alert'
        ELSE 'approve'
    END AS action
FROM full_txns AS txn
LEFT JOIN merchant_tags AS merchant ON merchant.id = txn.merchant_tags
WHERE txn.transaction_time < %(end_time)s::timestamptz
ORDER BY txn.transaction_time ASC, txn.id ASC;
