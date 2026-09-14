"""ML-backed chess player service."""

from __future__ import annotations

from dataclasses import dataclass

from services.inference import ONNXPolicyPredictor
from services.ml_config import (
    get_model_metadata_path,
    get_model_onnx_path,
)


@dataclass(frozen=True)
class MoveProposal:
    """Move proposed by an automated chess player."""

    from_square: str
    to_square: str
    promotion: str | None


class MLPlayer:
    """Backend service for generating moves with a trained policy model."""

    def __init__(self) -> None:
        self.predictor = ONNXPolicyPredictor(
            get_model_onnx_path(),
            get_model_metadata_path(),
        )

    def predict_move(
        self,
        fen: str,
    ) -> MoveProposal:
        """Return a model-generated move proposal."""

        prediction = self.predictor.predict(fen)

        return MoveProposal(
            from_square=prediction.from_square,
            to_square=prediction.to_square,
            promotion=prediction.promotion,
        )
