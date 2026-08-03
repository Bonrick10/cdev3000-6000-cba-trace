WITH previous AS (
    SELECT id, label
    FROM transactions
    WHERE id = %(transaction_id)s
    FOR UPDATE
),
updated AS (
    UPDATE transactions AS txn
    SET label = %(new_label)s
    FROM previous
    WHERE txn.id = previous.id
      AND previous.label IS DISTINCT FROM %(new_label)s
    RETURNING txn.id
)
INSERT INTO corrections (
    transaction_id,
    old_label,
    new_label,
    correction_time
)
SELECT
    previous.id,
    previous.label,
    %(new_label)s,
    %(correction_time)s
FROM previous
JOIN updated ON updated.id = previous.id
RETURNING id, transaction_id, old_label::text, new_label::text, correction_time;
