""" Prediction of new transaction's label """ 

def predict(model, X): 
    # Note that X is a list of inputFields here not single transaction
    return model.predict(X)