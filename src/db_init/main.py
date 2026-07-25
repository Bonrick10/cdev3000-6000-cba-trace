""" Main Module """
from src.db_init.populate_data import generate_seed_data, gen_all_txns

if __name__ == '__main__': 
    generate_seed_data()
    gen_all_txns()
