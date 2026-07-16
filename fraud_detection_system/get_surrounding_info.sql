-- SELECT 
--   json_build_object(
--     'device_seen_before', EXISTS (
--       SELECT device_sessions.id 
--       FROM device_sessions
--       WHERE 
--         device_session.entity_id = (
--           SELECT entities.id
--           FROM 
--             entities 
--             INNER JOIN accounts ON accounts.entity_id == entities.id
--           WHERE 
--             accounts.bsb = %(sender_bsb)s
--             AND accounts.account_number = %(sender_account_number)s
--         )
--         device_session.device_id = %(transactions)s
--     ), 
--     'merchant_thresholds', CASE WHEN %(merchant_tags)s IS NOT NULL THEN
--       json_build_object(
--       'suspicious_threshold_lower', merchant_tags.suspicious_threshold_lower,
--       'usual_threshold_lower', merchant_tags.usual_threshold_lower,
--       'usual_threshold_upper', merchant_tags.usual_threshold_upper,
--       'suspicious_threshold_upper', merchant_tags.suspicious_threshold_upper
--     ) ELSE NULL END,
--     '24_hour_spending', (
--       SELECT COALESCE(SUM(transactions.amount), 0.0::money)
--       FROM transactions
--       WHERE 
--         transactions.sender_bsb = %(sender_bsb)s
--         AND transactions.sender_account_number = %(sender_account_number)s
--         AND transactions.transaction_time >= %(transaction_time)s::timestamptz - INTERVAL '24 hours' -- Just switch to past 24 hours instead of day since UTC timestamp will make it annoying to deal with "current day"
--         AND transactions.transaction_time <= %(transaction_time)s::timestamptz 
--     ),
--     'seven_day_spending', (
--       SELECT COALESCE(SUM(transactions.amount), 0.0::money)
--       FROM transactions
--       WHERE 
--         transactions.sender_bsb = %(sender_bsb)s
--         AND transactions.sender_account_number = %(sender_account_number)s
--         AND transactions.transaction_time >= %(transaction_time)s::timestamptz - INTERVAL '7 days'
--         AND transactions.transaction_time <= %(transaction_time)s::timestamptz
--     ),
--     'last_transaction_time', transactions.transaction_time,
--     'last_transaction_longitude', transactions.sender_longitude,
--     'last_transaction_lattitude', transactions.sender_latitude,
--     'is_new_payee', NOT EXISTS(
--       SELECT 
--         transactions.id
--       FROM 
--         transactions
--       WHERE 
--         transactions.sender_bsb = %(sender_bsb)s
--         AND transactions.sender_account_number = %(sender_account_number)s
--         AND transactions.receiver_bsb = %(receiver_bsb)s
--         AND transactions.receiver_account_number = %(receiver_account_number)s
--     )
--   )
--   FROM
--     device_sessions
--     LEFT JOIN merchant_tags ON merchant_tags.id = %(merchant_tags)s
--     LEFT JOIN transactions ON (
--       transactions.sender_bsb = %(sender_bsb)s 
--       AND transactions.sender_account_number = %(sender_account_number)s
--     )
--   WHERE 
--     device_sessions.id = %(session_id)s
--   ORDER BY 
--     transactions.transaction_time
--   LIMIT 1


WITH new_transaction AS ( -- make a new virtual transaction, and make everything else relative to it 
  SELECT
    %(sender_bsb)s AS sender_bsb,
    %(sender_account_number)s AS sender_account_number,
    %(receiver_bsb)s AS receiver_bsb,
    %(receiver_account_number)s AS receiver_account_number,
    %(amount)s AS amount,
    %(transaction_time)s::timestamptz AS transaction_time,
    %(sender_latitude)s AS sender_latitude,
    %(sender_longitude)s AS sender_longitude,
    %(merchant_tags)s AS merchant_tags,
    %(device_id)s AS device_id
),
entity AS (
  SELECT entities.id AS id 
  FROM 
    entities 
    INNER JOIN accounts ON accounts.entity_id == entities.id
    WHERE 
      accounts.bsb = new_transaction.sender_bsb
      AND accounts.account_number = new_transaction.sender_account_number
),
period_spending AS (
  SELECT 
    COALESCE(SUM(transactions.amount) FILTER WHERE transactions.transaction_time >= new_transaction.transaction_time - INTERVAL '24 hours', 0.0::money) AS 24_hour,
    COALESCE(SUM(transactions.amount), 0.0::money) AS 7_day
  FROM transactions
  WHERE 
    transactions.sender_bsb = new_transaction.sender_bsb
    AND transactions.sender_account_number = new_transaction.sender_account_number
    AND transactions.transaction_time >= new_transaction.transaction_time - INTERVAL '7 days'
    AND transactions.transaction_time <= new_transaction.transaction_time    
),
last_transaction AS (
  SELECT 
    transactions.transaction_time,
    transactions.sender_latitude,
    transactions.sender_longitude
  FROM transactions
  WHERE 
    transactions.sender_bsb = new_transaction.sender_bsb
    AND transactions.sender_account_number = new_transaction.sender_account_number
    AND transactions.transaction_time <= new_transaction.transaction_time
  ORDER BY 
    new_transaction.transaction_time DESC 
  LIMIT 1
),
merchant_thresholds AS (
  SELECT
    merchant_tags.suspicious_threshold_lower,
    merchant_tags.usual_threshold_lower,
    merchant_tags.usual_threshold_upper,
    merchant_tags.suspicious_threshold_upper
  FROM merchant_tags
  WHERE merchant_tags.id = new_transaction.merchant_tags
),
SELECT json_build_object(
  'device_seen_before', EXISTS (
    SELECT 1
    FROM device_sessions
    WHERE 
      device_sessions.entity_id = entity.id
      AND device_sessions.device_id = new_transaction.device_id
  ),
  '24_hour_spending', period_spending.24_hour,-- note that this excludes new transaction 
  '7_day_spending', period_spending.7_day,
  'last_transaction_time', last_transaction.transaction_time,
  'last_transaction_longitude', last_transaction.sender_longitude,
  'last_transaction_lattitude', last_transaction.sender_latitude,
  'is_new_payee', NOT EXISTS(
      SELECT 
        transactions.id
      FROM 
        transactions
      WHERE 
        transactions.sender_bsb = new_transaction.sender_bsb
        AND transactions.sender_account_number = new_transaction.sender_account_number
        AND transactions.receiver_bsb = new_transaction.sender_account_number
        AND transactions.receiver_account_number = new_transaction.receiver_account_number
  ),
  'suspicious_threshold_lower', merchant_thresholds.suspicious_threshold_lower,
  'usual_threshold_lower', merchant_thresholds.usual_threshold_lower,
  'usual_threshold_upper', merchant_thresholds.usual_threshold_upper,
  'suspicious_threshold_upper', merchant_thresholds.suspicious_threshold_upper

)
FROM new_transaction
CROSS JOIN entity 
CROSS JOIN period_spending
LEFT JOIN last_transaction ON TRUE; -- These two may be NULL
LEFT JOIN merchant_thresholds ON TRUE;
