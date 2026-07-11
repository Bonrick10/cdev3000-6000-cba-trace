""" Read and Process Data from Database into format readable to model """

import os
from dotenv import load_dotenv
import psycopg2
import pandas
import numpy

load_dotenv() # load local environment variables from .env

def read_data():
    print("Reading Data")
    # This only gets transaction data for now for basic implementation 
    # TODO: Later join with more table information to give more info to model 
    query = """
        SELECT * 
        FROM transactions
        WHERE transactions.transaction_time < NOW() - INTERVAL '60 days'
    """
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    data_frame = pandas.read_sql(query, conn)
    conn.close()
    return data_frame

def process_data(data_frame):
    print("Processing Data")
    # Preprocess Data
    # TODO: Change fields into numeric value e.g. below
    # data_frame["Gender"] = data_frame["Gender"].map({"Male" : 1 , "Female" : 0})
    # data_frame['Married'] = data_frame['Married'].map({"Yes" : 1 , "No" : 0})
    # data_frame['Education'] = data_frame['Education'].map({'Graduate': 1 , 'Not Graduate' : 0})
    # data_frame['Dependents'] = data_frame['Dependents'].replace('3+' ,3)
    # data_frame['Self_Employed'] = data_frame['Self_Employed'].map({'Yes': 1 , 'No': 0})
    # data_frame['Property_Area'] = data_frame['Property_Area'].map({'Semiurban' : 1 , 'Urban': 2 , 'Rural': 3})
    # data_frame['Loan_Status'] = data_frame['Loan_Status'].map({'Y' : 1 , 'N' : 0})

    # Null Values Imputation
    # TODO: Change null into appropriate default value e.g. below
    # rev_null=['Gender','Married','Dependents','Self_Employed','Credit_History','LoanAmount','Loan_Amount_Term']
    # data_frame[rev_null]=data_frame[rev_null].replace({numpy.nan:data_frame['Gender'].mode(),
    #                                    numpy.nan:data_frame['Married'].mode(),
    #                                    numpy.nan:data_frame['Dependents'].mode(),
    #                                    numpy.nan:data_frame['Self_Employed'].mode(),
    #                                    numpy.nan:data_frame['Credit_History'].mode(),
    #                                    numpy.nan:data_frame['LoanAmount'].mean(),
    #                                    numpy.nan:data_frame['Loan_Amount_Term'].mean()})
    return data_frame

print(read_data())