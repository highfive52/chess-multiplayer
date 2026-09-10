import os
from pathlib import Path


ML_MODEL_PATH_ENV = "ML_MODEL_PATH"
ML_MODEL_METADATA_PATH_ENV = "ML_MODEL_METADATA_PATH"


def get_model_path() -> Path:
    value = os.environ.get(ML_MODEL_PATH_ENV)

    if not value:
        raise RuntimeError(f"{ML_MODEL_PATH_ENV} is not set")

    return Path(value)


def get_model_metadata_path() -> Path:
    value = os.environ.get(ML_MODEL_METADATA_PATH_ENV)

    if not value:
        raise RuntimeError(f"{ML_MODEL_METADATA_PATH_ENV} is not set")

    return Path(value)
