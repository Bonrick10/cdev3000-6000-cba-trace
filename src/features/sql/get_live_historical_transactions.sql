SELECT
    txn.id AS transaction_id,
    txn.sender_bsb,
    txn.sender_account_number,
    txn.receiver_bsb,
    txn.receiver_account_number,
    txn.amount::numeric::double precision AS amount,
    txn.transaction_time,
    txn.sender_latitude::double precision AS sender_latitude,
    txn.sender_longitude::double precision AS sender_longitude,
    COALESCE(latest_correction.new_label, txn.true_label)::text AS label,
    CASE
        WHEN latest_correction.new_label = 'confirmed_fraudulent'
            THEN 'reported_fraud'
        ELSE COALESCE(
            decision.final_label::text,
            first_correction.old_label,
            txn.predicted_label::text
        )
    END AS observed_label,
    COALESCE(merchant.merchant_category, txn.merchant_tags::text, 'unknown') AS merchant_tag,
    TRIM(txn.device_id) AS device_id,
    COALESCE(
        decision.rules_label::text,
        CASE
            WHEN first_correction.old_label IN (
                'rule_approval',
                'rule_alert',
                'rule_violation'
            )
            THEN first_correction.old_label
        END
    ) AS rules_label,
    COALESCE(
        decision.action,
        CASE WHEN first_correction.old_label = 'rule_violation' THEN 'block' END
    ) AS action
FROM transactions AS txn
LEFT JOIN transaction_decisions AS decision ON decision.transaction_id = txn.id
LEFT JOIN merchant_tags AS merchant ON merchant.id = txn.merchant_tags
LEFT JOIN LATERAL (
    SELECT correction.new_label
    FROM corrections AS correction
    WHERE correction.transaction_id = txn.id
    ORDER BY correction.correction_time DESC, correction.id DESC
    LIMIT 1
) AS latest_correction ON TRUE
LEFT JOIN LATERAL (
    SELECT correction.old_label::text AS old_label
    FROM corrections AS correction
    WHERE correction.transaction_id = txn.id
    ORDER BY correction.correction_time ASC, correction.id ASC
    LIMIT 1
) AS first_correction ON TRUE
WHERE txn.transaction_time < %(end_time)s::timestamptz
ORDER BY txn.transaction_time ASC, txn.id ASC;
