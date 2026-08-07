"""Data Population Module"""

import random
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
from geopy.distance import geodesic

import db_init.gen_tools as gen_tools
from db_init.txn_gen_tools.device_tools import choose_known_device, gen_new_device_id
from db_init.txn_gen_tools.mer_tools import get_merchant_legitimate_amount
from db_init.txn_gen_tools.loc_tools import gen_near_loc
from utils.db import NeonDB

BASE_DIR = Path(__file__).resolve().parent
SQL_DIR = BASE_DIR / "sql"
SRC_DIR = BASE_DIR.parent
BASE_TIME = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)  # 2023-01-01 00:00:00+00
# BASE_TIME = datetime(2024, 5, 22, 20, 5, 0, tzinfo=timezone.utc)  # 2023-01-01 00:00:00+00
END_TIME = datetime(
    2024, 6, 30, 23, 59, 59, tzinfo=timezone.utc
)  # 2026-06-30 23:59:59+00

BLINDSPOT = datetime(
    2024, 4, 30, 23, 59, 59, tzinfo=timezone.utc
)  # 2026-06-30 23:59:59+00

STING_START_TIME_1 = datetime(
    2024, 6, 18, 0, 0, 0, tzinfo=timezone.utc
)  # 2023-01-01 00:00:00+00
STING_END_TIME_1 = datetime(
    2024, 6, 21, 23, 59, 59, tzinfo=timezone.utc
)  # 2023-01-01 00:00:00+00
STING_START_TIME_2 = datetime(
    2024, 6, 25, 0, 0, 0, tzinfo=timezone.utc
)  # 2023-01-01 00:00:00+00
STING_END_TIME_2 = datetime(
    2024, 6, 28, 23, 59, 59, tzinfo=timezone.utc
)  # 2023-01-01 00:00:00+00

GIVEN_NAMES = [
    "John",
    "Jane",
    "Michael",
    "Emily",
    "David",
    "Sarah",
    "James",
    "Olivia",
    "William",
    "Emma",
    "Benjamin",
    "Ava",
    "Lucas",
    "Sophia",
    "Mason",
    "Isabella",
    "Ethan",
    "Mia",
    "Alexander",
    "Charlotte",
]
SURNAMES = [
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez",
    "Hernandez",
    "Lopez",
    "Gonzalez",
    "Wilson",
    "Anderson",
]


def generate_seed_data():
    """Populates the database with synthetic data."""
    db = NeonDB()
    print("Resetting database")
    db.execute(db.read_sql_file(SQL_DIR / "clear_all_tables.sql"))
    print("Generating data")
    db.execute(db.read_sql_file(SQL_DIR / "synthetic_population.sql"))


def init_sting_txns():
    # Create 5 new accounts and entities and store them in a sting table

    def random_date():
        start = date(1950, 1, 1)
        end = date(2000, 12, 31)

        delta_days = (end - start).days
        offset = random.randint(0, delta_days)
        return start + timedelta(days=offset)

    db = NeonDB()

    branches = db.query("SELECT * FROM branches")

    acc_counter = 501
    ent_counter = 51
    for _ in range(5):
        given_name = random.choice(GIVEN_NAMES)
        surname = random.choice(SURNAMES)
        dob = random_date()

        branch = random.choice(branches)
        bsb = branch["bsb"]
        funds = round(random.random() * 10000, 2)

        account_number = (acc_counter * 7919) % 900000000 + 100000000
        entity_id = (ent_counter * 7919) % 90000 + 100000

        lat = random.uniform(-90, 90)
        lon = random.uniform(-180, 180)

        lat = round(lat, 6)
        lon = round(lon, 6)

        acc_counter += 1
        ent_counter += 1

        entity = {
            "id": entity_id,
            "given_name": given_name,
            "surname": surname,
            "date_of_birth": dob,
        }

        account = {
            "bsb": bsb,
            "account_number": account_number,
            "funds": funds,
            "entity_id": entity_id,
        }

        sting = {
            "bsb": bsb,
            "account_number": account_number,
            "latitude": lat,
            "longitude": lon,
        }

        db.execute(
            """
            INSERT INTO entities (
                id,
                given_name,
                surname,
                date_of_birth
            ) VALUES (
                %(id)s,
                %(given_name)s,
                %(surname)s,
                %(date_of_birth)s                                                             
            );
            """,
            entity,
        )

        db.execute(
            """
            INSERT INTO accounts (
                bsb,
                account_number,
                funds,
                entity_id
            ) VALUES (
                %(bsb)s,
                %(account_number)s,
                %(funds)s,
                %(entity_id)s
            );
            """,
            account,
        )

        db.execute(
            """INSERT INTO stings (
                bsb,
                account_number,
                latitude,
                longitude
            ) VALUES (
                %(bsb)s,
                %(account_number)s,
                %(latitude)s,
                %(longitude)s   
            );
            """,
            sting,
        )


def gen_sting_txns():
    def sting_txn_time():
        # Pick which range to use
        start, end = random.choice(
            [
                (STING_START_TIME_1, STING_END_TIME_1),
                (STING_START_TIME_2, STING_END_TIME_2),
            ]
        )

        # Compute total seconds in the chosen range
        delta_seconds = int((end - start).total_seconds())

        # Pick a random offset
        offset = random.randint(0, delta_seconds)

        return start + timedelta(seconds=offset)

    def vary_lat_lon(lat, lon):
        radius_km = 1
        # Pick a random bearing (0–360 degrees)
        bearing = random.uniform(0, 360)

        # Pick a random distance inside the circle (uniform distribution)
        distance = radius_km * (random.random() ** 0.5)

        # Compute the destination point
        new_point = geodesic(kilometers=distance).destination((lat, lon), bearing)

        return round(new_point.latitude, 6), round(new_point.longitude, 6)

    db = NeonDB()

    accounts = db.query("""SELECT *
        FROM accounts a
        WHERE a.is_merchant = FALSE
            AND NOT EXISTS (
                SELECT 1
                FROM stings s
                WHERE s.bsb = a.bsb
                AND s.account_number = a.account_number
            );
        """)
    stings = db.query("SELECT * FROM stings;")

    for n in range(1000):
        print(f"Generating {n} sting txn out of 1000")
        txn_time = sting_txn_time()
        seed_account = random.choice(accounts)
        sting = random.choice(stings)

        amount = round(random.uniform(500, 1000), 2)

        merchant_tag = None
        lat, lon = vary_lat_lon(sting["latitude"], sting["longitude"])
        device_id = gen_new_device_id(seed_account["entity_id"], txn_time, db)

        txn = {
            "sender_bsb": seed_account["bsb"],
            "sender_account_number": seed_account["account_number"],
            "receiver_bsb": sting["bsb"],
            "receiver_account_number": sting["account_number"],
            "amount": amount,
            "transaction_time": txn_time,
            "sender_latitude": lat,
            "sender_longitude": lon,
            "predicted_label": predicted_label,
            "true_label": "confirmed_fraudulent",
            "merchant_tags": merchant_tag,
            "device_id": device_id,
        }
        insert_txn(txn, db, "sting_txns")


def fix_sting_txns_device():
    db = NeonDB()
    sting_txns = db.query("SELECT * FROM sting_txns;")
    for txn in sting_txns:
        # Update the device_id of this transaction to a new device_id
        account_txns = db.query(
            """
            SELECT *
            FROM transactions
            WHERE sender_bsb = %(bsb)s AND sender_account_number = %(account_number)s AND transaction_time < %(txn_time)s
            ORDER BY transaction_time DESC
        """,
            {
                "bsb": txn["sender_bsb"],
                "account_number": txn["sender_account_number"],
                "txn_time": txn["transaction_time"],
            },
        )

        entity_id = db.query(
            """
            SELECT entity_id
            FROM accounts
            WHERE bsb = %(bsb)s AND account_number = %(account_number)s
            LIMIT 1;
        """,
            {"bsb": txn["sender_bsb"], "account_number": txn["sender_account_number"]},
        )[0]["entity_id"]

        new_device_id = choose_known_device(
            entity_id, account_txns, txn["transaction_time"], db
        )
        db.execute(
            """
            UPDATE sting_txns
            SET device_id = %(new_device_id)s
            WHERE id = %(txn_id)s;
        """,
            {"new_device_id": new_device_id, "txn_id": txn["id"]},
        )


def gen_high_freq_txns():
    db = NeonDB()
    accounts = db.query("SELECT * FROM accounts WHERE is_merchant = FALSE;")
    merchants = db.query("SELECT * FROM accounts WHERE is_merchant = TRUE;")
    merchant_tags = {
        merchant_tag["id"]: merchant_tag
        for merchant_tag in db.query("""
        SELECT
            merchant_tags.id,
            merchant_tags.merchant_category,
            merchant_tags.suspicious_threshold_lower::numeric AS suspicious_threshold_lower,
            merchant_tags.usual_threshold_lower::numeric AS usual_threshold_lower,
            merchant_tags.usual_threshold_upper::numeric AS usual_threshold_upper,
            merchant_tags.suspicious_threshold_upper::numeric AS suspicious_threshold_upper
        FROM merchant_tags
        """)
    }

    for n in range(1000):
        print(f"Generating {n} high frequency txn out of 1000")
        delta_seconds = int((END_TIME - BASE_TIME).total_seconds())
        offset = random.randint(0, delta_seconds)

        txn_time = BASE_TIME + timedelta(seconds=offset)

        account = random.choice(accounts)
        merchant = random.choice(merchants)
        account_txns = db.query(
            """
            SELECT *
            FROM transactions
            WHERE sender_bsb = %(bsb)s AND sender_account_number = %(account_number)s AND transaction_time < %(txn_time)s
            ORDER BY transaction_time DESC
        """,
            {
                "bsb": account["bsb"],
                "account_number": account["account_number"],
                "txn_time": txn_time,
            },
        )

        base_amount = get_merchant_legitimate_amount(
            merchant_tags[merchant["merchant_tag"]]
        )

        for m in range(10):
            print(f"Generating {m} txn out of 10")
            amount = round(random.uniform(base_amount * 0.9, base_amount * 1.1), 2)
            lat, lon = gen_near_loc(account_txns)
            device_id = choose_known_device(
                account["entity_id"], account_txns, txn_time, db
            )

            if txn_time > BLINDSPOT:
                predicted_label = "reported_fraud"
            else:
                predicted_label = "legitimate"

            txn = {
                "sender_bsb": account["bsb"],
                "sender_account_number": account["account_number"],
                "receiver_bsb": merchant["bsb"],
                "receiver_account_number": merchant["account_number"],
                "amount": amount,
                "transaction_time": txn_time,
                "sender_latitude": lat,
                "sender_longitude": lon,
                "predicted_label": predicted_label,
                "true_label": "confirmed_fraudulent",
                "merchant_tags": merchant["merchant_tag"],
                "device_id": device_id,
            }
            insert_txn(txn, db, "high_freq_txns")

            txn_time += timedelta(
                minutes=random.randint(1, 2)
            )  # Increment time for next transaction


def gen_all_txns():
    db = NeonDB()

    # db.execute(db.read_sql_file(SQL_DIR / "clear_testing_tables.sql"))
    # RIP Memory usage 💀
    # Array of account dicts
    accounts = db.query("SELECT * FROM accounts WHERE is_merchant = FALSE;")
    # Array of account dicts
    merchants = db.query("SELECT * FROM accounts WHERE is_merchant = TRUE;")
    # Dict mapping merchant_tags.id to merchant_tag
    merchant_tags = {
        merchant_tag["id"]: merchant_tag
        for merchant_tag in db.query("""
        SELECT
            merchant_tags.id,
            merchant_tags.merchant_category,
            merchant_tags.suspicious_threshold_lower::numeric AS suspicious_threshold_lower,
            merchant_tags.usual_threshold_lower::numeric AS usual_threshold_lower,
            merchant_tags.usual_threshold_upper::numeric AS usual_threshold_upper,
            merchant_tags.suspicious_threshold_upper::numeric AS suspicious_threshold_upper
        FROM merchant_tags
        """)
    }
    # Array of device_ids
    device_sessions = db.query("SELECT * FROM device_sessions;")

    # Key is tuple of (bsb, account_number) value is arr of transaction dicts
    # (should be ascending time ordered since insert in order of timeline)
    account_txns = {
        (account["bsb"], account["account_number"]): [] for account in accounts
    }

    timeline = gen_tools.gen_timeline(BASE_TIME, END_TIME)

    print("Generating Transaction Data")
    for index, new_txn_time in enumerate(timeline):
        seed_account = random.choice(accounts)
        seed_acc_txns = account_txns[
            (seed_account["bsb"], seed_account["account_number"])
        ]

        print(f"\rGenerating Transaction {index} of {len(timeline)}")
        new_txns = gen_tools.gen_txn(
            seed_account,
            seed_acc_txns,
            accounts,
            merchants,
            merchant_tags,
            device_sessions,
            new_txn_time,
            db,
        )
        for new_txn in new_txns:
            account_txns[(seed_account["bsb"], seed_account["account_number"])].append(
                new_txn
            )
            insert_txn(new_txn, db)


# def maybe_gen_correction(transaction, db):
#     # 0.1% chance of correction
#     if random.random() > 0.001:
#         return None

#     old_label = transaction["label"]

#     if old_label == "legitimate" or old_label == "unusual" or old_label == "suspicious":
#         new_label = random.choice(["confirmed_legitimate", "confirmed_fraud"])


#     # Correction timing
#     day_delta = timedelta(days=random.randint(3, 60))
#     hour_delta = timedelta(hours=random.randint(0, 23))
#     minute_delta = timedelta(minutes=random.randint(0, 59))
#     delta = day_delta + hour_delta + minute_delta

#     correction_time = transaction["transaction_time"] + delta

#     correction = {
#         "transaction_id": transaction["id"],
#         "old_label": old_label,
#         "new_label": new_label,
#         "correction_time": correction_time
#     }
#     db.execute(
#         """
#         INSERT INTO corrections (transaction_id, old_label, new_label, correction_time)
#         VALUES (%(transaction_id)s, %(old_label)s, %(new_label)s, %(correction_time)s)
#         """, correction)


def insert_txn(txn, db, table="transactions"):
    """Insert a transaction into the database.

    Args:
        txn: Dictionary containing transaction details.
        db: NeonDB instance for database operations.

    """
    sql = f"""
    INSERT INTO {table} (
        sender_bsb, sender_account_number, receiver_bsb, receiver_account_number,
        amount, transaction_time, sender_latitude, sender_longitude, predicted_label,
        true_label, merchant_tags, device_id
    )
    VALUES (
        %(sender_bsb)s, %(sender_account_number)s, %(receiver_bsb)s, %(receiver_account_number)s,
        %(amount)s, %(transaction_time)s, %(sender_latitude)s, %(sender_longitude)s, %(predicted_label)s,
        %(true_label)s, %(merchant_tags)s, %(device_id)s
    )
    """

    db.execute(sql, txn)
