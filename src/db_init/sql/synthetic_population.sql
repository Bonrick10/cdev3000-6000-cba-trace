INSERT INTO branches (bsb, branch_location)
SELECT
    (g * 7919) % 90000 + 100000,
    (ARRAY['Sydney','Melbourne','Brisbane','Perth','Adelaide','Canberra',
    'Hobart','Darwin','Gold Coast','Newcastle','Wollongong','Geelong',
    'Townsville','Cairns','Toowoomba','Ballarat','Bendigo',
    'Sunshine Coast','Launceston', 'Rockhampton','Mackay','Bundaberg','Hervey Bay',
    'Coffs Harbour','Port Macquarie','Tamworth','Armidale','Orange','Bathurst',
    'Albury','Wagga Wagga','Shepparton','Mildura','Warrnambool',
    'Bunbury','Geraldton','Kalgoorlie','Alice Springs','Mount Isa'] )[1 + (random() * 38)::int] AS branch_location
FROM generate_series(1, 500) g;

INSERT INTO entities (id, given_name, surname, date_of_birth)
SELECT 
    (g * 7919) % 90000 + 100000,
    (ARRAY['John','Jane','Michael','Emily','David','Sarah','James','Olivia',
    'William','Emma','Benjamin','Ava','Lucas','Sophia','Mason','Isabella',
    'Ethan','Mia','Alexander','Charlotte'] )[1 + (random() * 19)::int] AS given_name,
    (ARRAY['Smith','Johnson','Williams','Brown','Jones','Garcia','Miller',
    'Davis','Rodriguez','Martinez','Hernandez','Lopez','Gonzalez',
    'Wilson','Anderson'] )[1 + (random() * 14)::int] AS surname,
    date '1950-01-01' + (random() * (date '2000-12-31' - date '1950-01-01'))::int AS date_of_birth
FROM generate_series(1, 50) g;

INSERT INTO merchant_tags (
    id,
    merchant_category,
    suspicious_threshold_lower,
    usual_threshold_lower,
    usual_threshold_upper,
    suspicious_threshold_upper
)
VALUES
(5411, 'Groceries',                 1.00,     10.00,      250.00,     1000.00),
(5541, 'Fuel Station',              3.00,     20.00,      180.00,      500.00),
(5812, 'Restaurant',                2.00,     10.00,      200.00,      750.00),
(5814, 'Fast Food',                 1.00,      5.00,       40.00,      200.00),
(5815, 'Coffee Shop',               1.00,      3.00,       25.00,      100.00),
(5311, 'Department Store',          5.00,     20.00,      600.00,     2500.00),
(5732, 'Electronics',              10.00,     50.00,     2500.00,     6000.00),
(5262, 'Online Marketplace',        2.00,     10.00,      800.00,     3000.00),
(5912, 'Pharmacy',                  1.00,      5.00,      150.00,      500.00),
(8011, 'Medical Services',          5.00,     40.00,      600.00,     3000.00),
(8062, 'Hospital',                 50.00,    200.00,    10000.00,    25000.00),
(7011, 'Hotel',                    20.00,    100.00,     1200.00,     5000.00),
(4511, 'Airline',                  20.00,    100.00,     2500.00,     8000.00),
(4111, 'Public Transport',          0.50,      2.00,       30.00,      150.00),
(4121, 'Taxi/Rideshare',            2.00,      8.00,      120.00,      500.00),
(4898, 'Subscription Service',      1.00,      5.00,       80.00,      300.00),
(4899, 'Streaming Service',         1.00,      5.00,       40.00,      150.00),
(4900, 'Utility Bills',             5.00,     30.00,      400.00,     1200.00),
(4814, 'Telecommunications',        3.00,     20.00,      200.00,      800.00),
(6300, 'Insurance',                10.00,     50.00,      700.00,     3000.00),
(9399, 'Government Services',       5.00,     20.00,     1000.00,     5000.00),
(8220, 'Education',                10.00,     50.00,     3000.00,    12000.00),
(8398, 'Charity',                   1.00,      5.00,      250.00,     2000.00),
(6011, 'ATM Withdrawal',            5.00,     20.00,      500.00,     2000.00),
(6010, 'Cash Advance',             10.00,     50.00,      800.00,     2500.00),
(5094, 'Jewellery',                20.00,    100.00,     5000.00,    15000.00),
(5948, 'Luxury Retail',            40.00,    200.00,     4000.00,    12000.00),
(7994, 'Gaming',                    1.00,      5.00,      100.00,      500.00),
(5921, 'Liquor Store',              2.00,     10.00,      150.00,      600.00),
(5072, 'Hardware Store',            5.00,     20.00,      800.00,     3000.00),
(5200, 'Home Improvement',         10.00,     50.00,     3000.00,     8000.00),
(5995, 'Pet Supplies',              2.00,     10.00,      250.00,     1000.00),
(5941, 'Sporting Goods',            5.00,     20.00,      700.00,     2500.00),
(5977, 'Beauty & Cosmetics',        2.00,     10.00,      250.00,     1000.00),
(5942, 'Bookstore',                 1.00,      5.00,      100.00,      500.00),
(5651, 'Clothing',                  5.00,     20.00,      600.00,     2500.00),
(5499, 'Convenience Store',         0.50,      2.00,       80.00,      300.00),
(4722, 'Travel Agency',            40.00,    200.00,     5000.00,    12000.00),
(7372, 'Digital Services',          1.00,      5.00,      200.00,     1000.00),
(6051, 'Cryptocurrency Exchange',  10.00,     50.00,     5000.00,    10000.00);

-- INSERT INTO device_sessions (id, entity_id, device_id, session_start_time, session_end_time)
-- SELECT
--     (g * 7919) % 90000 + 100000 AS id,
--     e.id AS entity_id,
--     MD5(g::text) AS device_id,
--     s.session_start_time,
--     CASE
--         WHEN random() < 0.3 THEN NULL
--         ELSE s.session_start_time + (random() * interval '4 hours')
--     END AS session_end_time
-- FROM generate_series(1, 100) g
-- CROSS JOIN LATERAL (
--     SELECT id
--     FROM entities
--     ORDER BY random() + g
--     LIMIT 1
-- ) e
-- CROSS JOIN LATERAL (
--     SELECT
--         '2023-01-01 00:00:00'::timestamp
--         + (random() * extract(epoch FROM ('2026-06-30 23:59:59'::timestamp - '2023-01-01 00:00:00'::timestamp))) 
--         * interval '1 second'
--         AS session_start_time
-- ) s;

INSERT INTO accounts (bsb, account_number, entity_id, funds, is_merchant, merchant_tag)
SELECT
    b.bsb,
    (100000000 + (g * 7919) % 900000000) AS account_number,
    e.id,
    (random() * 10000)::numeric(10,2) AS funds,
    CASE WHEN g <= 400 THEN FALSE ELSE TRUE END AS is_merchant,
    CASE WHEN g > 400 THEN m.id END AS merchant_tag
FROM generate_series(1, 500) g
CROSS JOIN LATERAL (
    SELECT bsb
    FROM branches
    ORDER BY random() + g
    LIMIT 1
) b
CROSS JOIN LATERAL (
    SELECT id
    FROM entities
    ORDER BY random() + g
    LIMIT 1
) e
CROSS JOIN LATERAL (
    SELECT id
    FROM merchant_tags
    ORDER BY random() + g
    LIMIT 1
) m
;