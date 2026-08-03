CREATE TABLE IF NOT EXISTS transaction_decisions (
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

ALTER TABLE transaction_decisions
    ADD COLUMN IF NOT EXISTS big_model_evidence JSONB,
    ADD COLUMN IF NOT EXISTS decision_source TEXT,
    ADD COLUMN IF NOT EXISTS decision_reason TEXT;

ALTER TABLE corrections
    ALTER COLUMN transaction_id TYPE BIGINT,
    ALTER COLUMN transaction_id DROP DEFAULT;
