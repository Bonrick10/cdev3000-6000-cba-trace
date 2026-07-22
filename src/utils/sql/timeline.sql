base_time := '2023-01-01 00:00:00'::timestamp;
end_time := '2026-06-30 23:59:59'::timestamp;

DROP TABLE IF EXISTS synthetic_timeline;

CREATE TABLE synthetic_timeline (
    id BIGSERIAL PRIMARY KEY,
    txn_time timestamptz NOT NULL
);

INSERT INTO synthetic_timeline (txn_time)
SELECT
    base_time + (g * interval '5 minutes') AS txn_time
FROM generate_series(1, floor(extract(epoch FROM (end_time - base_time)) / 300)) g;