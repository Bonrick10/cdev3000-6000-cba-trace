# cdev3000-6000-cba-trace
## Setup 
### Environment Setup 
- `python3 -m venv venv` - Make a new python virtual environment, do this once during setup 
- `source venv/bin/activate` Use the newly created python virtual environment - Do this every time you open up a new terminal 
- `pip install -r requirements.txt` - Use this to install necessary libraries for this project, Do this during initial setup, and also if new libraries are added
- Copy `.env.example` into `.env` and change environment variables to appropriate values
### Database Setup 
- To read in schema to remote db use `psql 'postgresql://[user]:[password]@[neon_hostname][:port]/[dbname]' -f ./schema.sql`
    - Only do this if neon remote db isn't already set up or to reset it.

## During Development
- `pip freeze > requirements.txt` - Use when you pip install something to save the list of libraries used 
## Cheat Sheet 
### Labels
- _confirmed\_legitimate_ - confirmed by customer to be legitimate
- _legitimate_ - Fraud detection system determines transaction to be normal - lets transaction through
- _unusual_ - Fraud detection system determines transaction to be outside of usual behaviour - lets transaction through
- _suspicious_ - Fraud detection system determines transaction to be potential fraud/scam - blocks transaction 
- _confirmed\_fraudulent_ - confirmed by customer to be fraud, done after transaction has already gone through (uncaught by fraud detection system)
- _rule\_violation_ - violates ruleset - instantly blocked before reaches model
### Rules/Scenarios
1. Transaction made from a previously unseen device associated with the customer -> _unusual_ 
2. Total spending exceeds customer's weekly average within a single day -> _unusual_
3. Two transactions made more than 500km apart per hour -> _suspicious_
4. Transactions in excess of $10 000 to new payees -> _unusual_ 
5. Transactions outside of normal range for merchant type -> _unusual_  
6. Transactions far exceed normal range for merchant type -> _suspicious_
**Emerging Fraud trend not included in ruleset**
7. TODO