CREATE TYPE account_type AS ENUM('savings', 'transactions');
CREATE TYPE transaction_label AS ENUM('legitimate', 'unusual', 'suspicious');

CREATE TABLE entities (
    id BIGSERIAL PRIMARY KEY,
    given_name VARCHAR(64) NOT NULL,
    surname VARCHAR(64) NOT NULL,
    date_of_birth date NOT NULL
);

CREATE TABLE accounts ( 
    id BIGSERIAL PRIMARY KEY,
    entity_id BIGINT NOT NULL REFERENCES entities(id),
    account_type account_type NOT NULL,
    daily_spending money DEFAULT 0.0 CHECK (daily_spending >= 0.0::money),-- likely to cause update anomalies 
    weekly_spending money DEFAULT 0.0 CHECK (daily_spending >= 0.0::money) -- likely to cause update anomalies 
    -- could create a trigger for the above two when new transaction inserted but it would be difficult to remove transactions once it leaves the time window
);

CREATE TABLE merchant_tags (
    id BIGSERIAL PRIMARY KEY,
    suspicious_threshold_upper money CHECK (suspicious_threshold_upper >= 0.0::money),
    suspicious_threshold_lower money CHECK (suspicious_threshold_lower >= 0.0::money),

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
    sender_id BIGINT NOT NULL REFERENCES accounts(id), 
    recipient_id BIGINT NOT NULL REFERENCES accounts(id), -- TODO: handle sender/receiver outside of system, e.g. non CBA customer
    amount money NOT NULL CHECK (amount >= 0.0::money),
    transaction_time timestamptz NOT NULL,
    sender_latitude Decimal(8,6) CHECK (sender_latitude >= -90 AND sender_latitude <= 90),
    sender_longitude Decimal(9,6) CHECK (sender_longitude >= -180 AND sender_longitude <= 180), -- https://stackoverflow.com/a/1196429
    label transaction_label, -- note this is the most up to date label after any corrections
    merchant_tags BIGINT REFERENCES merchant_tags(id),
    session_id BIGINT NOT NULL REFERENCES device_sessions(id)
);  

CREATE TABLE corrections (
    id BIGSERIAL PRIMARY KEY,
    transaction_id BIGSERIAL NOT NULL REFERENCES transactions(id),
    old_label transaction_label NOT NULL,
    new_label transaction_label NOT NULL,
    correction_time timestamptz NOT NULL,

    CONSTRAINT not_same_label CHECK (old_label != new_label)
);