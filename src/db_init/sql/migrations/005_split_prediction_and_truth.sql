-- Preserve the system decision separately from customer-confirmed truth.
-- The conditional rename supports databases created from the earlier schema;
-- current Neon databases that already use predicted_label are unchanged.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'transactions'
          AND column_name = 'label'
    ) AND NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'transactions'
          AND column_name = 'predicted_label'
    ) THEN
        ALTER TABLE transactions RENAME COLUMN label TO predicted_label;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'transactions'
          AND column_name = 'true_label'
    ) THEN
        ALTER TABLE transactions ADD COLUMN true_label transaction_label;
    END IF;
END
$$;

ALTER TABLE transactions ALTER COLUMN predicted_label DROP NOT NULL;
