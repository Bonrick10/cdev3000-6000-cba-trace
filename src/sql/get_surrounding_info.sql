-- note that no data validation, assumes all the IDs are in the db, as data validation low priority and not main focus of this project
-- Also note that tried to use SQL subqueries instead of sending multiple queries through psycopg2 to minimise latency (but subqueries are still pretty bad)
-- Although with CTEs it is possible that the query optimiser will efficiently combine some of them to not do subqueries 
WITH period_spending AS (
  SELECT 
    COALESCE(SUM(transactions.amount) FILTER (WHERE transactions.transaction_time >= %(transaction_time)s::timestamptz - INTERVAL '24 hours'), 0.0::money) AS "24_hour",
    COALESCE(SUM(transactions.amount), 0.0::money) AS "7_day"
  FROM transactions
  WHERE 
    transactions.sender_bsb = %(sender_bsb)s
    AND transactions.sender_account_number = %(sender_account_number)s
    AND transactions.transaction_time >=  %(transaction_time)s::timestamptz - INTERVAL '7 days'
    AND transactions.transaction_time <=  %(transaction_time)s::timestamptz -- exclude future rows past this timestamp
),
sender_entity AS (
  SELECT entities.id
  FROM 
    entities 
    INNER JOIN accounts ON accounts.entity_id = entities.id
    WHERE 
      accounts.bsb = %(sender_bsb)s
      AND accounts.account_number = %(sender_account_number)s
),
transaction_history_metadata AS (
  SELECT
    MIN(transactions.transaction_time) AS first_transaction_time,
    -- MAX(transactions.transaction_time) AS last_transaction_time, -- should be same as below 
    COUNT(*) AS num_transactions
  FROM transactions
   WHERE 
    transactions.sender_bsb = %(sender_bsb)s
    AND transactions.sender_account_number = %(sender_account_number)s
    AND transactions.transaction_time <= %(transaction_time)s::timestamptz -- exclude future rows past this timestamp
),
last_transaction AS (
  -- Too cursed to try merge this in with above transaction_history query 
  SELECT 
    transactions.transaction_time,
    transactions.sender_latitude,
    transactions.sender_longitude
  FROM transactions
  WHERE 
    transactions.sender_bsb = %(sender_bsb)s
    AND transactions.sender_account_number = %(sender_account_number)s
    AND transactions.transaction_time <= %(transaction_time)s::timestamptz -- exclude future rows past this timestamp
  ORDER BY transactions.transaction_time DESC 
  LIMIT 1
),
num_recurring AS (
  SELECT COUNT(id)
    FROM transactions
    WHERE
      transactions.sender_bsb = %(sender_bsb)s
      AND transactions.sender_account_number = %(sender_account_number)s
      AND transactions.receiver_bsb = %(receiver_bsb)s
      AND transactions.receiver_account_number = %(receiver_account_number)s
      AND transactions.transaction_time <=  %(transaction_time)s::timestamptz - INTERVAL '%(RECURRING_TXN_AGE_THRESHOLD_DAYS)s days' -- older than 7 days
      AND transactions.amount::numeric BETWEEN (%(amount)s - %(RECURRING_TXN_AMOUNT_VARIANCE)s) AND (%(amount)s + %(RECURRING_TXN_AMOUNT_VARIANCE)s) -- within +- $5
      AND LEAST( -- thanks AI 
          ABS((EXTRACT(HOUR FROM transactions.transaction_time::time) * 60 + EXTRACT(MINUTE FROM transactions.transaction_time::time)) -
              (EXTRACT(HOUR FROM %(transaction_time)s::time) * 60 + EXTRACT(MINUTE FROM %(transaction_time)s::time))),
          1440 - ABS((EXTRACT(HOUR FROM transactions.transaction_time::time) * 60 + EXTRACT(MINUTE FROM transactions.transaction_time::time)) -
                  (EXTRACT(HOUR FROM %(transaction_time)s::time) * 60 + EXTRACT(MINUTE FROM %(transaction_time)s::time))) --1440 to wrap midnight
      ) <= %(RECURRING_TXN_TIME_VARIANCE_MINUTES)s -- within 30 min time of day 
)
SELECT json_build_object(
  'device_seen_before', EXISTS (
    SELECT 1
    FROM 
      device_sessions
      CROSS JOIN sender_entity
    WHERE 
      device_sessions.entity_id = sender_entity.id
      AND device_sessions.device_id = %(device_id)s
      AND device_sessions.session_start_time <= %(transaction_time)s::timestamptz -- exclude future rows past this timestamp
  ),
  'entity_id', sender_entity.id,
  '24_hour_spending', period_spending."24_hour"::numeric,-- note that this excludes the pending new transaction 
  '7_day_spending', period_spending."7_day"::numeric,
  'first_transaction_time', transaction_history_metadata.first_transaction_time,
  'num_transactions', transaction_history_metadata.num_transactions,
  'last_transaction_time', last_transaction.transaction_time,
  'last_transaction_longitude', last_transaction.sender_longitude,
  'last_transaction_latitude', last_transaction.sender_latitude,
  'is_new_payee', NOT EXISTS(
      SELECT 1
      FROM transactions
      WHERE 
        transactions.sender_bsb = %(sender_bsb)s
        AND transactions.sender_account_number = %(sender_account_number)s
        AND transactions.receiver_bsb = %(receiver_bsb)s
        AND transactions.receiver_account_number = %(receiver_account_number)s
        AND transactions.transaction_time <= %(transaction_time)s::timestamptz -- exclude future rows past this timestamp
  ),
  'suspicious_threshold_lower', merchant_tags.suspicious_threshold_lower::numeric,
  'usual_threshold_lower', merchant_tags.usual_threshold_lower::numeric,
  'usual_threshold_upper', merchant_tags.usual_threshold_upper::numeric,
  'suspicious_threshold_upper', merchant_tags.suspicious_threshold_upper::numeric,
  'num_recurring', num_recurring.count
)
FROM 
  period_spending
  CROSS JOIN sender_entity
  CROSS JOIN transaction_history_metadata
  CROSS JOIN num_recurring
  LEFT JOIN merchant_tags ON merchant_tags.id = %(merchant_tags)s -- These two may be NULL
  LEFT JOIN last_transaction ON TRUE;
