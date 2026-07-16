CREATE TYPE transaction_label AS ENUM('confirmed_legitimate', 'legitimate', 'unusual', 'suspicious', 'confirmed_fraudulent', 'rule_violation'); -- note that fraudulent covers both fraud and scam here

CREATE TABLE entities (
    id BIGSERIAL PRIMARY KEY,
    given_name VARCHAR(64) NOT NULL,
    surname VARCHAR(64) NOT NULL,
    date_of_birth date NOT NULL
);

CREATE TABLE branches (
    bsb INTEGER PRIMARY KEY CHECK (bsb >= 100000 AND bsb <= 999999),
    branch_location VARCHAR(64), -- suburb for now I guess 
);

CREATE TABLE accounts (
    bsb INTEGER REFERENCES branches(bsb),
    account_number INTEGER CHECK (account_number > 0), -- not a set amount of digit range for account number 
    account_name VARCHAR(64),
    funds MONEY NOT NULL CHECK (funds >= 0.0::MONEY) DEFAULT 0.0::MONEY ,

    PRIMARY KEY (bsb, account_number)
);

CREATE TABLE merchant_tags (
    id BIGSERIAL PRIMARY KEY,
    merchant_category VARCHAR(64) NOT NULL 
    suspicious_threshold_lower MONEY CHECK (suspicious_threshold_lower >= 0.0::MONEY) NOT NULL,
    usual_threshold_lower MONEY CHECK (usual_threshold_lower >= 0.0::MONEY) NOT NULL,
    usual_threshold_upper MONEY CHECK (usual_threshold_upper >= 0.0::MONEY) NOT NULL,
    suspicious_threshold_upper MONEY CHECK (suspicious_threshold_upper >= 0.0::MONEY) NOT NULL,

    CONSTRAINT usual_lower_gt_suspicious_lower CHECK (usual_threshold_lower >= suspicious_threshold_lower),
    CONSTRAINT usual_upper_gt_usual_lower CHECK (usual_threshold_upper >= usual_threshold_lower),
    CONSTRAINT suspicious_upper_gt_usual_upper CHECK (suspicious_threshold_upper >= usual_threshold_upper)
);

CREATE TABLE device_sessions (
    -- was going to make (entity_id, device_id) a primary key but that would make it annoying for transactions to 
    -- reference this table since would have to store both fields 
    id BIGSERIAL PRIMARY KEY, 
    entity_id BIGINT NOT NULL REFERENCES entities(id),
    device_id CHAR(64) NOT NULL,  -- alternatively session token 
    session_start_time timestamptz NOT NULL,
    session_end_time timestamptz,

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