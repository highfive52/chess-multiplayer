"""Shared inference contracts for chess move prediction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class MovePrediction:
    """One move prediction produced by a policy model."""

    from_square: str
    to_square: str
    promotion: str | None
    score: float
    model_version: str


class MovePredictor(Protocol):
    """Interface implemented by chess move predictors."""

    def predict(
        self,
        fen: str,
    ) -> MovePrediction:
        """Predict one move from a FEN position."""
        ...


def create_predictor(
    provider: str,
    *,
    model_path: str | Path | None = None,
    model_version: str | None = None,
    hf_inference_endpoint: str | None = None,
    hf_token: str | None = None,
) -> MovePredictor:
    """Create the configured chess move predictor."""

    if provider == "local":
        if model_path is None:
            raise ValueError("model_path is required for local inference")

        if model_version is None:
            raise ValueError("model_version is required for local inference")

        from chess_ml.local_inference import LocalPolicyPredictor

        return LocalPolicyPredictor(
            model_path,
            model_version=model_version,
        )

    elif provider == "huggingface":
        if not hf_inference_endpoint:
            raise ValueError(
                "hf_inference_endpoint is required for Hugging Face inference"
            )

        from chess_ml.hf_inference import HuggingFacePolicyPredictor

        return HuggingFacePolicyPredictor(
            hf_inference_endpoint,
            token=hf_token,
        )

    else:
        raise ValueError(f"Unsupported inference provider: {provider}")


def __getattr__(name: str):
    if name == "PolicyPredictor":
        from chess_ml.local_inference import LocalPolicyPredictor

        return LocalPolicyPredictor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
