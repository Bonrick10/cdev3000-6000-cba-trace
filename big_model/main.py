""" Big Model Example Workflow"""
import sklearn
from handle_data import read_data, process_data
from train import train_model
from test import test_model

# Heavily based upon below article 
# https://www.kaggle.com/code/alirezahasannejad/random-forest-classifier-tutorial/notebook
TEST_SIZE = 0.3

if __name__ == "__main__":
    data_frame = process_data(read_data())

    # Split data frame into input and output fields
    X = data_frame.drop(columns=['transaction_label']).values # X is input fields to model, everything except label
    y = data_frame['transaction_label'].values # y is output target field, we want it to predict label

    # Split again into train and test datasets
    # Currently this just splits it into 70% train, 30% test randomly
    # However in practice we would want to split based on time e.g. train is older than 120 days, test is 120-60 days
    # and <60 days is blind period not handled by big model, Time split more accurately reflects CBA's implementation and keeps fraud trends together
    X_train, X_test, y_train, y_test = sklearn.model_selection.train_test_split(X, y, test_size = TEST_SIZE, random_state = 0)

    # Standardise input fields so that they have mean of 0 and standard deviation of 1, potentially move this to different file
    standard_scaler = sklearn.preprocessing.StandardScaler()
    X_train = standard_scaler.fit_transform(X_train)
    X_test = standard_scaler.transform(X_test)

    # potenially save trained model so that can predict using it later
    # https://scikit-learn.org/stable/model_persistence.html, https://joblib.readthedocs.io/en/latest/index.html#module-joblib
    model = train_model(X_train, y_train)

    # In practice we will be using "predict" function a lot more on new transactions 
    test_model(model, X_test, y_test)

