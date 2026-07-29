WITH previous AS (
    SELECT id, label
    FROM transactions
    WHERE id = %(transaction_id)s
    FOR UPDATE
),
updated AS (
    UPDATE transactions AS t
    SET label = %(new_label)s
    FROM previous AS p
    WHERE t.id = p.id
      AND p.label IS DISTINCT FROM %(new_label)s
    RETURNING t.id
)
INSERT INTO corrections (
    transaction_id,
    old_label,
    new_label,
    correction_time
)
SELECT
    p.id,
    p.label,
    %(new_label)s,
    %(correction_time)s
FROM previous AS p
JOIN updated AS u ON u.id = p.id
RETURNING id, transaction_id, old_label::text, new_label::text, correction_time;
