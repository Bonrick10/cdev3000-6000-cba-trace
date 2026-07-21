Device session 
- id = 105028
- entity_id = 147514
- device_id = c20ad4d76fe97759aa27a0c99bff6710 
- start_time = 2026-05-24 01:24:11.734022+00
- end_time = NULL 

Sender Entity
- id = 147514

Sender Account 
- bsb = 101383
- account number = 101702585
- funds = $4,469.13

Receiver Account 
- bsb = 100379
- account number = 102431133
- funds = $4,491.16
- entity id = 112193

Merchant tag 
- id = 4111
- suspicious lower = $0.5
- unusual lower = $2.00
- unusual upper = $30.00
- suspicious upper = $150.00

Existing transaction from sender to receiver 
- amount = 10 
- transaction_time = 2026-06-01 00:00:00 (after session start but hasn't ended yet)
- sender lattitude = 0
- sender longitude = 0
- merchant tag -> points to one above 
- device id -> one in session above

New transaction from sender to receiver 
- amount = 20
- transaction_time = 2026-06-03 00:00:00+00 (2 days after last transaction - shuold be included in weekly total but not daily)
- sender lattitude = 1.0
- sender longitude = 1.0
- merchant tag -> points to one above 
- device id -> one in session above