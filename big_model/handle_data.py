""" Read and Process Data from Database into format readable to model """

import pandas
import numpy

def read_data():
    print("Reading Data")
    # TODO: Figure out import from NEON incl which fields to include
    # likely would have to join basically all tables
    # https://pandas.pydata.org/docs/reference/api/pandas.read_sql.html
    # May not even need db.py interface file
    # data_frame = pandas.read_csv("train.csv")
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