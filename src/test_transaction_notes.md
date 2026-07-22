Device session 
- id = 106411
- entity_id = 120866
- device_id = 14bfa6bb14875e45bba028a21ed38046    
- start_time = 2026-02-23 17:14:04.53408+00
- end_time = NULL 

Sender Entity
- id = 120866

Sender Account 
- bsb = 107040
- account number = 100736467
- funds = $7,837.02

<!-- Receiver Account 
- bsb = 100379
- account number = 102431133
- funds = $4,491.16
- entity id = 112193 -->
Receiver Account 
- bsb = 130547
- account number = 103325980
- funds = $5,253.56
- entity id = 125894
- merchant_tag = 4111


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