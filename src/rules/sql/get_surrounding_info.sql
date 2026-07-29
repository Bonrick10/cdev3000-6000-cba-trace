WITH completed_transactions AS (
    SELECT t.*
    FROM transactions AS t
    LEFT JOIN transaction_decisions AS d ON d.transaction_id = t.id
    WHERE COALESCE(
        d.action <> 'block',
        t.label IS DISTINCT FROM 'rule_violation'
        AND NOT EXISTS (
            SELECT 1
            FROM corrections AS c
            WHERE c.transaction_id = t.id
              AND c.old_label = 'rule_violation'
        )
    )
),
sender_entity AS (
    SELECT a.entity_id
    FROM accounts AS a
    WHERE a.bsb = %(sender_bsb)s
      AND a.account_number = %(sender_account_number)s
),
sender_history AS (
    SELECT
        COUNT(t.id) AS prior_transaction_count,
        MIN(t.transaction_time) AS first_transaction_time,
        AVG(t.amount::numeric) AS prior_mean_amount,
        STDDEV_POP(t.amount::numeric) AS prior_std_amount,
        COUNT(t.id) FILTER (
            WHERE t.transaction_time >= %(transaction_time)s::timestamptz - INTERVAL '24 hours'
        ) AS prior_24h_transaction_count,
        COUNT(t.id) FILTER (
            WHERE t.transaction_time >= %(transaction_time)s::timestamptz - INTERVAL '7 days'
        ) AS prior_7d_transaction_count,
        COALESCE(SUM(t.amount::numeric) FILTER (
            WHERE t.transaction_time >= %(transaction_time)s::timestamptz - INTERVAL '24 hours'
        ), 0) AS prior_24h_spend,
        COALESCE(SUM(t.amount::numeric) FILTER (
            WHERE t.transaction_time >= %(transaction_time)s::timestamptz - INTERVAL '7 days'
        ), 0) AS prior_7d_spend
    FROM completed_transactions AS t
    WHERE t.sender_bsb = %(sender_bsb)s
      AND t.sender_account_number = %(sender_account_number)s
      AND t.transaction_time < %(transaction_time)s::timestamptz
),
payee_history AS (
    SELECT COUNT(t.id) AS prior_payee_transaction_count
    FROM completed_transactions AS t
    WHERE t.sender_bsb = %(sender_bsb)s
      AND t.sender_account_number = %(sender_account_number)s
      AND t.receiver_bsb = %(receiver_bsb)s
      AND t.receiver_account_number = %(receiver_account_number)s
      AND t.transaction_time < %(transaction_time)s::timestamptz
),
device_history AS (
    SELECT COUNT(t.id) AS prior_device_transaction_count
    FROM completed_transactions AS t
    WHERE t.sender_bsb = %(sender_bsb)s
      AND t.sender_account_number = %(sender_account_number)s
      AND TRIM(t.device_id) = TRIM(%(device_id)s)
      AND t.transaction_time < %(transaction_time)s::timestamptz
),
device_session_history AS (
    SELECT EXISTS (
        SELECT 1
        FROM device_sessions AS ds
        CROSS JOIN sender_entity AS se
        WHERE ds.entity_id = se.entity_id
          AND TRIM(ds.device_id) = TRIM(%(device_id)s)
          AND ds.session_start_time < %(transaction_time)s::timestamptz
    ) AS device_seen_before
),
last_transaction AS (
    SELECT
        t.transaction_time AS last_transaction_time,
        t.sender_latitude::double precision AS last_transaction_latitude,
        t.sender_longitude::double precision AS last_transaction_longitude
    FROM completed_transactions AS t
    WHERE t.sender_bsb = %(sender_bsb)s
      AND t.sender_account_number = %(sender_account_number)s
      AND t.transaction_time < %(transaction_time)s::timestamptz
    ORDER BY t.transaction_time DESC, t.id DESC
    LIMIT 1
),
recurring_history AS (
    SELECT COUNT(t.id) AS num_recurring
    FROM completed_transactions AS t
    WHERE t.sender_bsb = %(sender_bsb)s
      AND t.sender_account_number = %(sender_account_number)s
      AND t.receiver_bsb = %(receiver_bsb)s
      AND t.receiver_account_number = %(receiver_account_number)s
      AND t.transaction_time < (
          %(transaction_time)s::timestamptz
          - %(recurring_age_days)s * INTERVAL '1 day'
      )
      AND t.amount::numeric BETWEEN
          %(amount)s - %(recurring_amount_variance)s
          AND %(amount)s + %(recurring_amount_variance)s
      AND LEAST(
          ABS(
              EXTRACT(HOUR FROM t.transaction_time) * 60
              + EXTRACT(MINUTE FROM t.transaction_time)
              - EXTRACT(HOUR FROM %(transaction_time)s::timestamptz) * 60
              - EXTRACT(MINUTE FROM %(transaction_time)s::timestamptz)
          ),
          1440 - ABS(
              EXTRACT(HOUR FROM t.transaction_time) * 60
              + EXTRACT(MINUTE FROM t.transaction_time)
              - EXTRACT(HOUR FROM %(transaction_time)s::timestamptz) * 60
              - EXTRACT(MINUTE FROM %(transaction_time)s::timestamptz)
          )
      ) <= %(recurring_time_variance_minutes)s
)
SELECT
    se.entity_id,
    dsh.device_seen_before,
    (ph.prior_payee_transaction_count = 0) AS is_new_payee,
    sh.prior_transaction_count,
    sh.first_transaction_time,
    sh.prior_mean_amount,
    COALESCE(sh.prior_std_amount, 0) AS prior_std_amount,
    sh.prior_24h_transaction_count,
    sh.prior_7d_transaction_count,
    sh.prior_24h_spend,
    sh.prior_7d_spend,
    ph.prior_payee_transaction_count,
    dh.prior_device_transaction_count,
    lt.last_transaction_time,
    lt.last_transaction_latitude,
    lt.last_transaction_longitude,
    rh.num_recurring,
    mt.merchant_category,
    mt.suspicious_threshold_lower::numeric AS suspicious_threshold_lower,
    mt.usual_threshold_lower::numeric AS usual_threshold_lower,
    mt.usual_threshold_upper::numeric AS usual_threshold_upper,
    mt.suspicious_threshold_upper::numeric AS suspicious_threshold_upper
FROM sender_entity AS se
CROSS JOIN sender_history AS sh
CROSS JOIN payee_history AS ph
CROSS JOIN device_history AS dh
CROSS JOIN device_session_history AS dsh
CROSS JOIN recurring_history AS rh
LEFT JOIN last_transaction AS lt ON TRUE
LEFT JOIN merchant_tags AS mt ON mt.id = %(merchant_tags)s;
