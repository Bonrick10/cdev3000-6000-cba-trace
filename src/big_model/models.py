"""Compatibility exports for the big-model public interface."""

from src.big_model.predict import predict_transaction
from src.big_model.train import fit_model, train_from_database

__all__ = ["fit_model", "predict_transaction", "train_from_database"]
