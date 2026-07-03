CREATE TYPE account_type AS ENUM('savings', 'transactions');
CREATE TYPE transaction_label AS ENUM('legitimate', 'unusual', 'suspicious');

CREATE TABLE entities (
    id BIGSERIAL PRIMARY KEY,
    given_name VARCHAR(64) NOT NULL,
    surname VARCHAR(64) NOT NULL,
    date_of_birth date NOT NULL
);

CREATE TABLE branches (
    bsb INTEGER PRIMARY KEY CHECK (bsb >= 100000 AND bsb <= 999999),
    branch_location VARCHAR(64), -- suburb for now I guess 
    is_internal BOOLEAN NOT NULL -- Did this instead of creating 2 child tables for internal and external since fields basically same
);

CREATE TABLE accounts (
    bsb INTEGER REFERENCES branches(bsb),
    account_number INTEGER CHECK (account_number > 0), -- not a set amount of digit range for account number 
    account_name VARCHAR(64),

    PRIMARY KEY (bsb, account_number)
);

CREATE TABLE internal_accounts ( 
    bsb INTEGER,
    account_number INTEGER,
    entity_id BIGINT NOT NULL REFERENCES entities(id),
    account_type account_type NOT NULL,
    funds MONEY NOT NULL CHECK (funds >= 0.0::MONEY),

    FOREIGN KEY (bsb, account_number) REFERENCES accounts(bsb, account_number),
    PRIMARY KEY (bsb, account_number)
);

CREATE TABLE merchant_tags (
    id BIGSERIAL PRIMARY KEY,
    suspicious_threshold_upper MONEY CHECK (suspicious_threshold_upper >= 0.0::MONEY),
    suspicious_threshold_lower MONEY CHECK (suspicious_threshold_lower >= 0.0::MONEY),

    CONSTRAINT check_upper_threshold_exceeds_lower CHECK ( suspicious_threshold_upper >= suspicious_threshold_lower)
);

CREATE TABLE device_sessions (
    -- was going to make (entity_id, device_id) a primary key but that would make it annoying for transactions to 
    -- reference this table since would have to store both fields 
    id BIGSERIAL PRIMARY KEY, 
    entity_id BIGINT REFERENCES entities(id),
    device_id CHAR(64),  -- alternatively session token 

    CONSTRAINT entity_device_uniqueness UNIQUE (entity_id, device_id)
);

CREATE TABLE transactions (
    id BIGSERIAL PRIMARY KEY,
    sender_bsb INTEGER NOT NULL, 
    sender_account_number INTEGER NOT NULL, 
    receiver_bsb INTEGER NOT NULL, 
    receiver_account_number INTEGER NOT NULL, 
    amount MONEY NOT NULL CHECK (amount >= 0.0::MONEY),
    transaction_time timestamptz NOT NULL,
    sender_latitude Decimal(8,6) CHECK (sender_latitude >= -90 AND sender_latitude <= 90),
    sender_longitude Decimal(9,6) CHECK (sender_longitude >= -180 AND sender_longitude <= 180), -- https://stackoverflow.com/a/1196429
    label transaction_label, -- note this is the most up to date label after any corrections
    merchant_tags BIGINT REFERENCES merchant_tags(id),
    session_id BIGINT NOT NULL REFERENCES device_sessions(id),

    FOREIGN KEY (sender_bsb, sender_account_number) REFERENCES accounts(bsb, account_number), -- potentially somehow check that at least one of sender/receiver is internal_account
    FOREIGN KEY (receiver_bsb, receiver_account_number) REFERENCES accounts(bsb, account_number)
);  

CREATE TABLE corrections (
    id BIGSERIAL PRIMARY KEY,
    transaction_id BIGSERIAL NOT NULL REFERENCES transactions(id),
    old_label transaction_label NOT NULL,
    new_label transaction_label NOT NULL,
    correction_time timestamptz NOT NULL,

    CONSTRAINT not_same_label CHECK (old_label != new_label)
);