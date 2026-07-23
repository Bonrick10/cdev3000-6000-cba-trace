Device session 
- id = 117975
- entity_id = 187109
- device_id = 8e296a067a37563370ded05f5a3bf3ec 
- start_time = 22022-09-14 00:00:00+00 (edited to be before transaction)
- end_time = NULL 

Sender Entity
- id = 187109

Sender Account 
- bsb = 108927
- account number = 102280672
- funds = $7382.92

Receiver Account 
- bsb = 147389
- account number = 103421008
- funds = $5,775.14
- entity id = 141732

Merchant tag 
- id = 5814
- suspicious lower = 147389
- unusual lower = $5.00
- unusual upper = $40.00
- suspicious upper = $200.00

Existing transaction from sender to receiver 
- amount = 8.04
- transaction_time = 2023-01-01 00:05:00+00 (after session start but hasn't ended yet)
- sender lattitude = 24.443799
- sender longitude = -138.757596
- merchant tag -> points to one above  5814
- device id -> one in session above 8e296a067a37563370ded05f5a3bf3ec      

New transaction from sender to receiver 
- amount = 20
- transaction_time = 2023-03-01 00:00:00+00 (2 days after last transaction - shuold be included in weekly total but not daily)
- sender lattitude = 24
- sender longitude = -138
- merchant tag -> points to one above 5814
- device id -> one in session above 8e296a067a37563370ded05f5a3bf3ec