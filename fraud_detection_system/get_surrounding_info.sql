SELECT 
  json_build_object(
    'device_seen_before', EXISTS (
      SELECT 
        device_sessions.id 
      FROM 
        device_sessions
      WHERE 
        device_session.entity_id = %(merchant_tags)s
        device_session.device_id = %(transactions)s
    ), 
    'merchant_thresholds', CASE WHEN %(merchant_tags)s IS NOT NULL THEN
      json_build_object(
      'suspicious_threshold_lower', merchant_tags.suspicious_threshold_lower,
      'usual_threshold_lower', merchant_tags.usual_threshold_lower,
      'usual_threshold_upper', merchant_tags.usual_threshold_upper,
      'suspicious_threshold_upper', merchant_tags.suspicious_threshold_upper
    ) ELSE NULL END,
    '24_hour_spending', (
      SELECT 
        COALESCE(SUM(transactions.amount), 0.0::money)
      FROM 
        transactions
      WHERE 
        transactions.sender_bsb = %(sender_bsb)s
        AND transactions.sender_account_number = %(sender_account_number)s
        AND transactions.transaction_time >= %(transaction_time)s::timestamptz - INTERVAL '24 hours' -- Just switch to past 24 hours instead of day since UTC timestamp will make it annoying to deal with "current day"
        AND transactions.transaction_time <= %(transaction_time)s::timestamptz 
    ),
    'seven_day_spending', (
      SELECT 
        COALESCE(SUM(transactions.amount), 0.0::money)
      FROM 
        transactions
      WHERE 
        transactions.sender_bsb = %(sender_bsb)s
        AND transactions.sender_account_number = %(sender_account_number)s
        AND transactions.transaction_time >= %(transaction_time)s::timestamptz - INTERVAL '7 days'
        AND transactions.transaction_time <= %(transaction_time)s::timestamptz
    ),
    'last_transaction_time', transactions.transaction_time,
    'last_transaction_longitude', transactions.sender_longitude,
    'last_transaction_lattitude', transactions.sender_latitude,
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
    )
  )
  FROM
    device_sessions
    LEFT JOIN merchant_tags ON merchant_tags.id = %(merchant_tags)s
    LEFT JOIN transactions ON (
      transactions.sender_bsb = %(sender_bsb)s 
      AND transactions.sender_account_number = %(sender_account_number)s
    )
  WHERE 
    device_sessions.id = %(session_id)s
  ORDER BY 
    transactions.transaction_time
  LIMIT 1