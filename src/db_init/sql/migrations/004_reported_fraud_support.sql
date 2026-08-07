-- ``reported_fraud`` is an observable customer-report status used only by the
-- small model. Ground truth remains in ``true_label`` and is never a feature.
ALTER TYPE transaction_label ADD VALUE IF NOT EXISTS 'reported_fraud';

-- Data generation owns creation/population of full_txns. Add its time index
-- when the table is present without making the migration depend on that job.
DO $$
BEGIN
    IF to_regclass('public.full_txns') IS NOT NULL THEN
        CREATE INDEX IF NOT EXISTS full_txns_time_idx
            ON full_txns(transaction_time, id);
    END IF;
END
$$;
