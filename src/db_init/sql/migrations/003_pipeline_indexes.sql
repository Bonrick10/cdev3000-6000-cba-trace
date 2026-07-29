CREATE INDEX IF NOT EXISTS transactions_sender_time_idx
    ON transactions(sender_bsb, sender_account_number, transaction_time, id);
CREATE INDEX IF NOT EXISTS transactions_payee_time_idx
    ON transactions(
        sender_bsb,
        sender_account_number,
        receiver_bsb,
        receiver_account_number,
        transaction_time
    );
CREATE INDEX IF NOT EXISTS transactions_device_time_idx
    ON transactions(sender_bsb, sender_account_number, device_id, transaction_time);
CREATE INDEX IF NOT EXISTS corrections_transaction_time_idx
    ON corrections(transaction_id, correction_time);
CREATE INDEX IF NOT EXISTS decisions_rules_label_idx
    ON transaction_decisions(rules_label);
