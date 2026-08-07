WITH previous AS (
    SELECT
        id,
        true_label,
        COALESCE(true_label, predicted_label) AS current_label
    FROM transactions
    WHERE id = %(transaction_id)s
    FOR UPDATE
),
updated AS (
    UPDATE transactions AS txn
    SET true_label = %(new_label)s
    FROM previous
    WHERE txn.id = previous.id
      AND previous.true_label IS DISTINCT FROM %(new_label)s
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
    previous.current_label,
    %(new_label)s,
    %(correction_time)s
FROM previous
JOIN updated ON updated.id = previous.id
RETURNING id, transaction_id, old_label::text, new_label::text, correction_time;
