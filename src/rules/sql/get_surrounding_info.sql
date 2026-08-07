WITH completed_transactions AS (
    SELECT txn.*
    FROM transactions AS txn
    LEFT JOIN transaction_decisions AS decision ON decision.transaction_id = txn.id
    WHERE COALESCE(
        decision.action <> 'block',
        txn.predicted_label IS DISTINCT FROM 'rule_violation'
        AND NOT EXISTS (
            SELECT 1
            FROM corrections AS correction
            WHERE correction.transaction_id = txn.id
              AND correction.old_label = 'rule_violation'
        )
    )
),
sender_entity AS (
    SELECT account.entity_id
    FROM accounts AS account
    WHERE account.bsb = %(sender_bsb)s
      AND account.account_number = %(sender_account_number)s
),
sender_history AS (
    SELECT
        COUNT(txn.id) AS prior_transaction_count,
        MIN(txn.transaction_time) AS first_transaction_time,
        AVG(txn.amount::numeric) AS prior_mean_amount,
        STDDEV_POP(txn.amount::numeric) AS prior_std_amount,
        COUNT(txn.id) FILTER (
            WHERE txn.transaction_time >= %(transaction_time)s::timestamptz - INTERVAL '24 hours'
        ) AS prior_24h_transaction_count,
        COUNT(txn.id) FILTER (
            WHERE txn.transaction_time >= %(transaction_time)s::timestamptz - INTERVAL '7 days'
        ) AS prior_7d_transaction_count,
        COALESCE(SUM(txn.amount::numeric) FILTER (
            WHERE txn.transaction_time >= %(transaction_time)s::timestamptz - INTERVAL '24 hours'
        ), 0) AS prior_24h_spend,
        COALESCE(SUM(txn.amount::numeric) FILTER (
            WHERE txn.transaction_time >= %(transaction_time)s::timestamptz - INTERVAL '7 days'
        ), 0) AS prior_7d_spend
    FROM completed_transactions AS txn
    WHERE txn.sender_bsb = %(sender_bsb)s
      AND txn.sender_account_number = %(sender_account_number)s
      AND txn.transaction_time < %(transaction_time)s::timestamptz
),
payee_history AS (
    SELECT COUNT(txn.id) AS prior_payee_transaction_count
    FROM completed_transactions AS txn
    WHERE txn.sender_bsb = %(sender_bsb)s
      AND txn.sender_account_number = %(sender_account_number)s
      AND txn.receiver_bsb = %(receiver_bsb)s
      AND txn.receiver_account_number = %(receiver_account_number)s
      AND txn.transaction_time < %(transaction_time)s::timestamptz
),
device_history AS (
    SELECT COUNT(txn.id) AS prior_device_transaction_count
    FROM completed_transactions AS txn
    WHERE txn.sender_bsb = %(sender_bsb)s
      AND txn.sender_account_number = %(sender_account_number)s
      AND TRIM(txn.device_id) = TRIM(%(device_id)s)
      AND txn.transaction_time < %(transaction_time)s::timestamptz
),
device_session_history AS (
    SELECT EXISTS (
        SELECT 1
        FROM device_sessions AS session
        CROSS JOIN sender_entity AS sender
        WHERE session.entity_id = sender.entity_id
          AND TRIM(session.device_id) = TRIM(%(device_id)s)
          AND session.session_start_time < %(transaction_time)s::timestamptz
    ) AS device_seen_before
),
last_transaction AS (
    SELECT
        txn.transaction_time AS last_transaction_time,
        txn.sender_latitude::double precision AS last_transaction_latitude,
        txn.sender_longitude::double precision AS last_transaction_longitude
    FROM completed_transactions AS txn
    WHERE txn.sender_bsb = %(sender_bsb)s
      AND txn.sender_account_number = %(sender_account_number)s
      AND txn.transaction_time < %(transaction_time)s::timestamptz
    ORDER BY txn.transaction_time DESC, txn.id DESC
    LIMIT 1
),
recurring_history AS (
    SELECT COUNT(txn.id) AS num_recurring
    FROM completed_transactions AS txn
    WHERE txn.sender_bsb = %(sender_bsb)s
      AND txn.sender_account_number = %(sender_account_number)s
      AND txn.receiver_bsb = %(receiver_bsb)s
      AND txn.receiver_account_number = %(receiver_account_number)s
      AND txn.transaction_time < (
          %(transaction_time)s::timestamptz
          - %(recurring_age_days)s * INTERVAL '1 day'
      )
      AND txn.amount::numeric BETWEEN
          %(amount)s - %(recurring_amount_variance)s
          AND %(amount)s + %(recurring_amount_variance)s
      AND LEAST(
          ABS(
              EXTRACT(HOUR FROM txn.transaction_time) * 60
              + EXTRACT(MINUTE FROM txn.transaction_time)
              - EXTRACT(HOUR FROM %(transaction_time)s::timestamptz) * 60
              - EXTRACT(MINUTE FROM %(transaction_time)s::timestamptz)
          ),
          1440 - ABS(
              EXTRACT(HOUR FROM txn.transaction_time) * 60
              + EXTRACT(MINUTE FROM txn.transaction_time)
              - EXTRACT(HOUR FROM %(transaction_time)s::timestamptz) * 60
              - EXTRACT(MINUTE FROM %(transaction_time)s::timestamptz)
          )
      ) <= %(recurring_time_variance_minutes)s
)
SELECT
    sender.entity_id,
    session_history.device_seen_before,
    (payee.prior_payee_transaction_count = 0) AS is_new_payee,
    history.prior_transaction_count,
    history.first_transaction_time,
    history.prior_mean_amount,
    COALESCE(history.prior_std_amount, 0) AS prior_std_amount,
    history.prior_24h_transaction_count,
    history.prior_7d_transaction_count,
    history.prior_24h_spend,
    history.prior_7d_spend,
    payee.prior_payee_transaction_count,
    device.prior_device_transaction_count,
    previous.last_transaction_time,
    previous.last_transaction_latitude,
    previous.last_transaction_longitude,
    recurring.num_recurring,
    merchant.merchant_category,
    merchant.suspicious_threshold_lower::numeric AS suspicious_threshold_lower,
    merchant.usual_threshold_lower::numeric AS usual_threshold_lower,
    merchant.usual_threshold_upper::numeric AS usual_threshold_upper,
    merchant.suspicious_threshold_upper::numeric AS suspicious_threshold_upper
FROM sender_entity AS sender
CROSS JOIN sender_history AS history
CROSS JOIN payee_history AS payee
CROSS JOIN device_history AS device
CROSS JOIN device_session_history AS session_history
CROSS JOIN recurring_history AS recurring
LEFT JOIN last_transaction AS previous ON TRUE
LEFT JOIN merchant_tags AS merchant ON merchant.id = %(merchant_tags)s;
