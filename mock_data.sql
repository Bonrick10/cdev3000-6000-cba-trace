INSERT INTO entities (given_name, surname, date_of_birth) VALUES ('test_given_name1', 'test_surname1', '2001-01-01');
INSERT INTO entities (given_name, surname, date_of_birth) VALUES ('test_given_name2', 'test_surname2', '2001-01-01');
INSERT INTO branches (bsb, branch_location, is_internal) VALUES (100000, 'Sydney', true);
INSERT INTO accounts (bsb, account_number, account_name) VALUES (100000, 1, 'test 1''s account');
INSERT INTO accounts (bsb, account_number, account_name) VALUES (100000, 2, 'test 2''s account');
INSERT INTO merchant_tags(suspicious_threshold_lower, usual_threshold_lower, usual_threshold_upper, suspicious_threshold_upper) VALUES (1.0, 10.0, 50.0, 100.0);
INSERT INTO device_sessions (entity_id, device_id, session_start_time) VALUES (1, 'test1''s device', '2000-01-01 00:00:00');
INSERT INTO device_sessions (entity_id, device_id, session_start_time) VALUES (2, 'test2''s device', '2000-01-01 00:00:00');

INSERT INTO transactions (sender_bsb, sender_account_number, receiver_bsb, receiver_account_number, amount, transaction_time, sender_latitude, sender_longitude, label, merchant_tags, session_id) VALUES (100000, 1, 100000, 2, 1.0, '2001-01-01 00:00:00', 0, 0, 'legitimate', 1, 1);
INSERT INTO transactions (sender_bsb, sender_account_number, receiver_bsb, receiver_account_number, amount, transaction_time, sender_latitude, sender_longitude, label, merchant_tags, session_id) VALUES (100000, 2, 100000, 1, 2.0, '2001-01-01 00:00:30', 0, 0, 'legitimate', 1, 2);