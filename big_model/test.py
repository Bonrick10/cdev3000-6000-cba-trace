""" Evaluation of large model """ 
from predict import predict
import sklearn

def test_model(model, X, y_actual):
    y_prediction = predict(model, X)

    # Compare prediction with actual
    print(sklearn.metrics.classification_report(y_prediction, y_actual))

    # view importance of each field to model
    print(model.feature_importances_)