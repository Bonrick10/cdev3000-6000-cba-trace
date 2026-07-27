"""
Runs when a user reports a transaction as fraud, the fraud detection system
1. Determines which cluster that transaction is in
2. Marks that transaction as confirmed_fraud
3. Check if number of transactions in cluster marked as fraud exceed threshold (eg. 10%)
4. If it does exceed suspect other transactions in cluster for fraud
    -> possibly call up or implement investigation process.
5. Re-cluster appropriately after fraudulent/legitimate labels are confirmed, to segregate
    confirmed legitimate cases and confirmed fraudulent cases,
    and sort unconfirmed legitimate cases.
6. Once clusters contain sufficient fraud, use Bayesian optimization to discover new rules.
"""
