from src.utils.db import NeonDB
import datetime

# WHERE
#   LEAST(
#     ABS(EXTRACT(EPOCH FROM ((ts AT TIME ZONE 'UTC')::time - :target))) / 60,
#     1440 - (ABS(EXTRACT(EPOCH FROM ((ts AT TIME ZONE 'UTC')::time - :target))) / 60)
#   ) <= 30

db = NeonDB()

target = datetime.datetime(year=2000,month=1,day=1,hour=00,minute=15)
print(db.query("""
    SELECT id, transaction_time
    FROM transactions
    WHERE
    LEAST(
        ABS((EXTRACT(HOUR FROM transactions.transaction_time) * 60 + EXTRACT(MINUTE FROM transactions.transaction_time)) -
            (EXTRACT(HOUR FROM %(target)s) * 60 + EXTRACT(MINUTE FROM %(target)s))),
        1440 - ABS((EXTRACT(HOUR FROM transactions.transaction_time) * 60 + EXTRACT(MINUTE FROM transactions.transaction_time)) -
                (EXTRACT(HOUR FROM %(target)s) * 60 + EXTRACT(MINUTE FROM %(target)s)))
    ) <= 30;
""", {"target": target.time()}))
