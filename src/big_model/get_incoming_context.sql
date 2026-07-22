WITH sender_history AS (
    SELECT
        COUNT(*) AS prior_transaction_count,

        MIN(t.transaction_time)
            AS first_transaction_time,

        AVG(t.amount::numeric)
            AS prior_mean_amount,

        STDDEV_POP(t.amount::numeric)
            AS prior_std_amount,

        COUNT(*) FILTER (
            WHERE
                t.transaction_time
                >= %(transaction_time)s::timestamptz
                   - INTERVAL '24 hours'
        ) AS prior_24h_transaction_count,

        COUNT(*) FILTER (
            WHERE
                t.transaction_time
                >= %(transaction_time)s::timestamptz
                   - INTERVAL '7 days'
        ) AS prior_7d_transaction_count,

        COALESCE(
            SUM(t.amount::numeric) FILTER (
                WHERE
                    t.transaction_time
                    >= %(transaction_time)s::timestamptz
                       - INTERVAL '24 hours'
            ),
            0
        ) AS prior_24h_spend,

        COALESCE(
            SUM(t.amount::numeric) FILTER (
                WHERE
                    t.transaction_time
                    >= %(transaction_time)s::timestamptz
                       - INTERVAL '7 days'
            ),
            0
        ) AS prior_7d_spend

    FROM transactions AS t

    WHERE
        t.sender_bsb = %(sender_bsb)s
        AND t.sender_account_number =
            %(sender_account_number)s
        AND t.transaction_time
            < %(transaction_time)s::timestamptz
),

payee_history AS (
    SELECT
        COUNT(*) AS prior_payee_transaction_count

    FROM transactions AS t

    WHERE
        t.sender_bsb = %(sender_bsb)s
        AND t.sender_account_number =
            %(sender_account_number)s
        AND t.receiver_bsb = %(receiver_bsb)s
        AND t.receiver_account_number =
            %(receiver_account_number)s
        AND t.transaction_time
            < %(transaction_time)s::timestamptz
),

device_history AS (
    SELECT
        COUNT(*) AS prior_device_transaction_count

    FROM transactions AS t

    WHERE
        t.sender_bsb = %(sender_bsb)s
        AND t.sender_account_number =
            %(sender_account_number)s
        AND TRIM(t.device_id) =
            TRIM(%(device_id)s)
        AND t.transaction_time
            < %(transaction_time)s::timestamptz
),

last_transaction AS (
    SELECT
        t.transaction_time
            AS last_transaction_time,

        t.sender_latitude::double precision
            AS last_transaction_latitude,

        t.sender_longitude::double precision
            AS last_transaction_longitude

    FROM transactions AS t

    WHERE
        t.sender_bsb = %(sender_bsb)s
        AND t.sender_account_number =
            %(sender_account_number)s
        AND t.transaction_time
            < %(transaction_time)s::timestamptz

    ORDER BY
        t.transaction_time DESC,
        t.id DESC

    LIMIT 1
)

SELECT json_build_object(
    'prior_transaction_count',
        sender_history.prior_transaction_count,

    'first_transaction_time',
        sender_history.first_transaction_time,

    'prior_mean_amount',
        sender_history.prior_mean_amount,

    'prior_std_amount',
        sender_history.prior_std_amount,

    'prior_24h_transaction_count',
        sender_history.prior_24h_transaction_count,

    'prior_7d_transaction_count',
        sender_history.prior_7d_transaction_count,

    'prior_24h_spend',
        sender_history.prior_24h_spend,

    'prior_7d_spend',
        sender_history.prior_7d_spend,

    'prior_payee_transaction_count',
        payee_history.prior_payee_transaction_count,

    'prior_device_transaction_count',
        device_history.prior_device_transaction_count,

    'last_transaction_time',
        last_transaction.last_transaction_time,

    'last_transaction_latitude',
        last_transaction.last_transaction_latitude,

    'last_transaction_longitude',
        last_transaction.last_transaction_longitude

) AS context

FROM sender_history

CROSS JOIN payee_history

CROSS JOIN device_history

LEFT JOIN last_transaction
    ON TRUE;