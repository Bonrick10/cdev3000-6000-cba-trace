# cdev3000-6000-cba-trace
## Setup 
# Environment Steps
- `python3 -m venv venv` - Make a new python virtual environment, do this once during setup 
- `source venv/bin/activate` Use the newly created python virtual environment - Do this every time you open up a new terminal 
- `pip install -r requirements.txt` - Use this to install necessary libraries for this project, Do this during initial setup, and also if new libraries are added
- Copy `.env.example` into `.env` and change environment variables to appropriate values
# Database setup 
- To read in schema to remote db use `psql 'postgresql://[user]:[password]@[neon_hostname][:port]/[dbname]' -f ./schema.sql`
    - Only do this if neon remote db isn't already set up or to reset it.

## During Development
- `pip freeze > requirements.txt` - Use when you pip install something to save the list of libraries used 
