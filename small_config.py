"""Shared settings for the standalone small fraud model."""

from pathlib import Path


BASE_DIRECTORY = Path(__file__).resolve().parent

MODEL_DIRECTORY = BASE_DIRECTORY / "models"

SMALL_MODEL_PATH = (
    MODEL_DIRECTORY / "small_model_current.joblib"
)

DATA_PATH = BASE_DIRECTORY / "transactions.csv"


MODEL_FEATURES = [
    "amount",
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "is_new_device",
    "is_new_payee",
    "spend_24h",
    "spend_7d",
    "distance_km",
]