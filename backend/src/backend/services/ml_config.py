"""ML inference configuration."""

from __future__ import annotations

import os
from pathlib import Path


def _resolve_repo_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path

    return (Path(__file__).resolve().parents[3] / path).resolve()


def get_inference_provider() -> str:
    """Return the configured ML inference provider."""

    provider = (
        os.environ.get(
            "ML_INFERENCE_PROVIDER",
            "local",
        )
        .strip()
        .lower()
    )

    if provider not in {"local", "huggingface"}:
        raise RuntimeError(f"Unsupported ML_INFERENCE_PROVIDER: {provider}")

    return provider


def get_model_path() -> Path:
    """Return the local policy model path."""

    value = os.environ.get("ML_MODEL_PATH")

    if not value:
        raise RuntimeError("ML_MODEL_PATH is not set")

    return _resolve_repo_path(value)


def get_model_metadata_path() -> Path:
    """Return the local policy metadata path."""

    value = os.environ.get("ML_MODEL_METADATA_PATH")

    if not value:
        raise RuntimeError("ML_MODEL_METADATA_PATH is not set")

    return _resolve_repo_path(value)


def get_hf_inference_endpoint() -> str:
    """Return the Hugging Face inference endpoint."""

    value = os.environ.get("HF_INFERENCE_ENDPOINT")

    if not value:
        raise RuntimeError("HF_INFERENCE_ENDPOINT is not set")

    return value


def get_hf_token() -> str | None:
    """Return the optional Hugging Face access token."""

    return os.environ.get("HF_TOKEN")
