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
last_transaction AS (
  SELECT 
    transactions.transaction_time,
    transactions.sender_latitude,
    transactions.sender_longitude
  FROM transactions
  WHERE 
    transactions.sender_bsb = %(sender_bsb)s
    AND transactions.sender_account_number = %(sender_account_number)s
    AND transactions.transaction_time <=  %(transaction_time)s::timestamptz -- exclude future rows past this timestamp
  ORDER BY 
     transactions.transaction_time DESC 
  LIMIT 1
)
SELECT json_build_object(
  'device_seen_before', EXISTS (
    SELECT 1
    FROM device_sessions
    WHERE 
      device_sessions.entity_id = (
        SELECT entities.id
        FROM 
          entities 
          INNER JOIN accounts ON accounts.entity_id = entities.id
          WHERE 
            accounts.bsb = %(sender_bsb)s
            AND accounts.account_number = %(sender_account_number)s
      )
      AND device_sessions.device_id = %(device_id)s
  ),
  '24_hour_spending', period_spending."24_hour",-- note that this excludes the pending new transaction 
  '7_day_spending', period_spending."7_day",
  'last_transaction_time', last_transaction.transaction_time,
  'last_transaction_longitude', last_transaction.sender_longitude,
  'last_transaction_lattitude', last_transaction.sender_latitude,
  'is_new_payee', NOT EXISTS(
      SELECT 
        transactions.id
      FROM 
        transactions
      WHERE 
        transactions.sender_bsb = %(sender_bsb)s
        AND transactions.sender_account_number = %(sender_account_number)s
        AND transactions.receiver_bsb = %(receiver_bsb)s
        AND transactions.receiver_account_number = %(receiver_account_number)s
  ),
  'suspicious_threshold_lower', merchant_tags.suspicious_threshold_lower,
  'usual_threshold_lower', merchant_tags.usual_threshold_lower,
  'usual_threshold_upper', merchant_tags.usual_threshold_upper,
  'suspicious_threshold_upper', merchant_tags.suspicious_threshold_upper
)
FROM period_spending
LEFT JOIN merchant_tags ON merchant_tags.id = %(merchant_tags)s -- These two may be NULL
LEFT JOIN last_transaction ON TRUE;
