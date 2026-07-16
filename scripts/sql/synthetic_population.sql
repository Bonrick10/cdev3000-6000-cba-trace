INSERT INTO branches (bsb, branch_location, is_internal)
SELECT
    g + 100000,
    (ARRAY['Sydney','Melbourne','Brisbane','Perth','Adelaide','Canberra',
    'Hobart','Darwin','Gold Coast','Newcastle','Wollongong','Geelong',
    'Townsville','Cairns','Toowoomba','Ballarat','Bendigo',
    'Sunshine Coast','Launceston',
    'Rockhampton','Mackay','Bundaberg','Hervey Bay','Coffs Harbour',
    'Port Macquarie','Tamworth','Armidale','Orange','Bathurst',
    'Albury','Wagga Wagga','Shepparton','Mildura','Warrnambool',
    'Bunbury','Geraldton','Kalgoorlie','Alice Springs','Mount Isa'] )[1 + (random() * 39)::int] AS branch_location,
    (random() < 0.5) AS is_internal
FROM generate_series(1, 50000) g;

INSERT INTO entities (id, given_name, surname, date_of_birth)
SELECT 
    g + 100000,
    (ARRAY['John','Jane','Michael','Emily','David','Sarah','James','Olivia',
    'William','Emma','Benjamin','Ava','Lucas','Sophia','Mason','Isabella',
    'Ethan','Mia','Alexander','Charlotte'] )[1 + (random() * 19)::int] AS given_name,
    (ARRAY['Smith','Johnson','Williams','Brown','Jones','Garcia','Miller',
    'Davis','Rodriguez','Martinez','Hernandez','Lopez','Gonzalez',
    'Wilson','Anderson'] )[1 + (random() * 14)::int] AS surname,
    date '1950-01-01' + (random() * (date '2000-12-31' - date '1950-01-01'))::int AS date_of_birth
FROM generate_series(1, 5000) g;

INSERT INTO accounts (bsb, account_number, account_name)
SELECT 
    (SELECT bsb FROM branches ORDER BY random() LIMIT 1) AS bsb,
    (random() * 8999999999 + 1000000000)::bigint AS account_number,
    (SELECT given_name || ' ' || surname FROM entities WHERE id = (SELECT id FROM entities ORDER BY random() LIMIT 1)) AS account_name
FROM generate_series(1, 100000) g;

INSERT INTO internal_accounts (bsb, account_number, entity_id, account_type, funds)
SELECT
    b.bsb,
    a.account_number,
    e.id,
    (ARRAY['savings','checking','credit'])[1 + (random() * 2)::int] AS account_type,
    (random() * 10000)::numeric(10,2) AS funds
FROM generate_series(1, 50000) g
CROSS JOIN LATERAL (
    SELECT bsb FROM branches WHERE is_internal = true ORDER BY random() LIMIT 1
) b
CROSS JOIN LATERAL (
    SELECT account_number FROM accounts WHERE bsb = b.bsb ORDER BY random() LIMIT 1
) a
CROSS JOIN LATERAL (
    SELECT id FROM entities ORDER BY random() LIMIT 1
) e;

INSERT INTO merchant_tags (
    id,
    merchant_category,
    sus_lower_lim,
    usual_lower_lim,
    usual_upper_lim,
    sus_upper_lim
)
VALUES
(5411, 'Groceries',                 1.00,      5.00,      250.00,     1000.00),
(5541, 'Fuel Station',              3.00,     20.00,      180.00,      500.00),
(5812, 'Restaurant',                2.00,     10.00,      200.00,      750.00),
(5814, 'Fast Food',                 1.00,      5.00,       40.00,      200.00),
(5814, 'Coffee Shop',               1.00,      3.00,       25.00,      100.00),
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
(4899, 'Subscription Service',      1.00,      5.00,       80.00,      300.00),
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


INSERT INTO device_sessions (id, entity_id, last_active)
SELECT
    g + 100000,
    (SELECT id FROM entities ORDER BY random() LIMIT 1) AS entity_id,
    NOW() - (random() * interval '365 days') AS last_active
FROM generate_series(1, 10000) g;