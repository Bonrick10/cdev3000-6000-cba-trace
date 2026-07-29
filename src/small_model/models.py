"""Compatibility exports for the small-model public interface."""

from src.small_model.predict import predict_transaction
from src.small_model.train import fit_small_model, train_from_database

__all__ = ["fit_small_model", "predict_transaction", "train_from_database"]
