TRUNCATE TABLE
    transaction_decisions,
    accounts,
    branches,
    corrections,
    device_sessions,
    entities,
    merchant_tags,
    txns_testing,
    transactions
RESTART IDENTITY CASCADE;
