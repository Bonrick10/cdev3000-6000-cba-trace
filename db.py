""" Database Interface """

import os
import collections
import psycopg2
from dotenv import load_dotenv

load_dotenv() # load local environment variables from .env

conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

def get_transaction(sender_bsb, sender_account_number):
    """ Get list of transaction details for a specified sender id """
    cur.execute("""
        SELECT *
        FROM transactions
        WHERE transactions.sender_bsb = %s AND transactions.sender_account_number = %s
    """, [sender_bsb, sender_account_number])
    print(cur.fetchall())
    return cur.fetchall()

def get_transaction_surrounding_info(transaction):
    """ Gets adjacent info for an incoming transaction to check against rules """

    # note that no data validation, assumes all the IDs are in the db
    # Data validation low priority and not main focus of this project
    # Also note that tried to use SQL subqueries instead of sending multiple queries through
    # psycopg2 to minimise latency (but subqueries are still pretty bad)
    cur.execute("""
        SELECT 
            json_build_object(
                'device_session', json_build_object(
                    'start_time', device_sessions.session_start_time,
                    'end_time', device_sessions.session_end_time
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
    """, collections.defaultdict(lambda: None, transaction))
    # ^ convert non entries into None - especially for merchant_tags which may not be provided

    return cur.fetchone()[0]

print(get_transaction_surrounding_info({
    "sender_bsb": 100000,
    "sender_account_number": 1,
    "receiver_bsb": 100000,
    "receiver_account_number": 2,
    "amount": 10,
    "transaction_time": "2001-01-03 00:00:00+00",
    "sender_latitude": 0.0,
    "sender_longitude": 0.0,
    "merchant_tags": 1, 
    "session_id": 1
}))
