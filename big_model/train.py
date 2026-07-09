""" Training of Large Model""" 

import sklearn

# X is input fields, y is target output field
def train_model(X, y):
    # TODO: Look into tweaking RandomForestClassifier fields, also make constants for magic numbers once done 
    # https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html#sklearn.ensemble.RandomForestClassifier
    model = sklearn.ensemble.RandomForestClassifier(n_estimators=100, criterion = 'entropy', random_state = 42)
    model.fit(X, y)

    return model