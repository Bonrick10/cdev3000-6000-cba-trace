CREATE TYPE transaction_label AS ENUM (
    'confirmed_legitimate',
    'legitimate',
    'unusual',
    'suspicious',
    'confirmed_fraudulent',
    'reported_fraud',
    'rule_violation',
    'rule_approval',
    'rule_alert'
);

CREATE TABLE entities (
    id BIGSERIAL PRIMARY KEY,
    given_name VARCHAR(64) NOT NULL,
    surname VARCHAR(64) NOT NULL,
    date_of_birth DATE NOT NULL
);

CREATE TABLE branches (
    bsb INTEGER PRIMARY KEY CHECK (bsb BETWEEN 100000 AND 999999),
    branch_location VARCHAR(64)
);

CREATE TABLE accounts (
    bsb INTEGER REFERENCES branches(bsb),
    account_number INTEGER CHECK (account_number > 0),
    entity_id BIGINT REFERENCES entities(id) NOT NULL,
    account_name VARCHAR(64),
    funds MONEY NOT NULL CHECK (funds >= 0.0::MONEY) DEFAULT 0.0::MONEY,
    is_merchant BOOLEAN NOT NULL DEFAULT FALSE,
    merchant_tag BIGINT REFERENCES merchant_tags(id),
    PRIMARY KEY (bsb, account_number)
);

CREATE TABLE merchant_tags (
    id BIGINT PRIMARY KEY,
    merchant_category VARCHAR(64) NOT NULL,
    suspicious_threshold_lower MONEY NOT NULL CHECK (
        suspicious_threshold_lower >= 0.0::MONEY
    ),
    usual_threshold_lower MONEY NOT NULL CHECK (usual_threshold_lower >= 0.0::MONEY),
    usual_threshold_upper MONEY NOT NULL CHECK (usual_threshold_upper >= 0.0::MONEY),
    suspicious_threshold_upper MONEY NOT NULL CHECK (
        suspicious_threshold_upper >= 0.0::MONEY
    ),
    CONSTRAINT usual_lower_gt_suspicious_lower CHECK (
        usual_threshold_lower >= suspicious_threshold_lower
    ),
    CONSTRAINT usual_upper_gt_usual_lower CHECK (
        usual_threshold_upper >= usual_threshold_lower
    ),
    CONSTRAINT suspicious_upper_gt_usual_upper CHECK (
        suspicious_threshold_upper >= usual_threshold_upper
    )
);

CREATE TABLE device_sessions (
    id BIGSERIAL PRIMARY KEY,
    entity_id BIGINT NOT NULL REFERENCES entities(id),
    device_id CHAR(64) NOT NULL,
    session_start_time TIMESTAMPTZ NOT NULL,
    session_end_time TIMESTAMPTZ
);

CREATE TABLE transactions (
    id BIGSERIAL PRIMARY KEY,
    sender_bsb INTEGER NOT NULL,
    sender_account_number INTEGER NOT NULL,
    receiver_bsb INTEGER NOT NULL,
    receiver_account_number INTEGER NOT NULL,
    amount MONEY NOT NULL CHECK (amount >= 0.0::MONEY),
    transaction_time TIMESTAMPTZ NOT NULL,
    sender_latitude DECIMAL(8,6) CHECK (sender_latitude BETWEEN -90 AND 90),
    sender_longitude DECIMAL(9,6) CHECK (sender_longitude BETWEEN -180 AND 180),
    predicted_label transaction_label,
    merchant_tags BIGINT REFERENCES merchant_tags(id),
    device_id CHAR(64) NOT NULL,
    true_label transaction_label,
    FOREIGN KEY (sender_bsb, sender_account_number)
        REFERENCES accounts(bsb, account_number),
    FOREIGN KEY (receiver_bsb, receiver_account_number)
        REFERENCES accounts(bsb, account_number)
);

-- Read-only development backup maintained by the data-generation workflow.
CREATE TABLE txns_testing (LIKE transactions INCLUDING ALL);

-- Canonical complete model-development snapshot. ``predicted_label`` is the
-- observable historical status; ``true_label`` is hidden ground truth.
CREATE TABLE full_txns (LIKE transactions INCLUDING ALL);

CREATE TABLE transaction_decisions (
    transaction_id BIGINT PRIMARY KEY REFERENCES transactions(id) ON DELETE CASCADE,
    rules_label transaction_label NOT NULL,
    rules_reasons TEXT[] NOT NULL DEFAULT '{}',
    big_model_label transaction_label,
    big_model_score DOUBLE PRECISION CHECK (big_model_score BETWEEN 0 AND 1),
    big_model_version TEXT,
    big_model_evidence JSONB,
    small_model_label transaction_label,
    small_model_version TEXT,
    small_cluster_id INTEGER,
    small_model_evidence JSONB,
    final_label transaction_label NOT NULL,
    decision_source TEXT NOT NULL,
    decision_reason TEXT NOT NULL,
    action VARCHAR(32) NOT NULL CHECK (
        action IN ('approve', 'approve_and_alert', 'block')
    ),
    decision_time TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE corrections (
    id BIGSERIAL PRIMARY KEY,
    transaction_id BIGINT NOT NULL REFERENCES transactions(id),
    old_label transaction_label NOT NULL,
    new_label transaction_label NOT NULL,
    correction_time TIMESTAMPTZ NOT NULL,
    CONSTRAINT not_same_label CHECK (old_label != new_label)
);

CREATE INDEX transactions_sender_time_idx
    ON transactions(sender_bsb, sender_account_number, transaction_time, id);
CREATE INDEX transactions_payee_time_idx
    ON transactions(
        sender_bsb,
        sender_account_number,
        receiver_bsb,
        receiver_account_number,
        transaction_time
    );
CREATE INDEX transactions_device_time_idx
    ON transactions(sender_bsb, sender_account_number, device_id, transaction_time);
CREATE INDEX txns_testing_time_idx ON txns_testing(transaction_time, id);
CREATE INDEX full_txns_time_idx ON full_txns(transaction_time, id);
CREATE INDEX corrections_transaction_time_idx
    ON corrections(transaction_id, correction_time);
CREATE INDEX decisions_rules_label_idx
    ON transaction_decisions(rules_label);
