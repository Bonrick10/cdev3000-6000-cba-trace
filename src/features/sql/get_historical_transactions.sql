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
    COALESCE(mt.merchant_category, t.merchant_tags::text, 'unknown') AS merchant_tag,
    TRIM(t.device_id) AS device_id,
    COALESCE(
        d.rules_label::text,
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
        d.action,
        CASE
            WHEN first_correction.old_label = 'rule_violation' THEN 'block'
        END
    ) AS action
FROM txns_testing AS t
LEFT JOIN transaction_decisions AS d ON d.transaction_id = t.id
LEFT JOIN merchant_tags AS mt ON mt.id = t.merchant_tags
LEFT JOIN LATERAL (
    SELECT c.old_label::text AS old_label
    FROM corrections AS c
    WHERE c.transaction_id = t.id
    ORDER BY c.correction_time ASC, c.id ASC
    LIMIT 1
) AS first_correction ON TRUE
WHERE t.transaction_time < %(end_time)s::timestamptz
ORDER BY t.transaction_time ASC, t.id ASC;
