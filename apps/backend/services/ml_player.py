"""ML-backed chess player service."""

from __future__ import annotations

from dataclasses import dataclass

from chess_ml.inference import MovePredictor

from services.ml_config import (
    get_hf_inference_endpoint,
    get_hf_token,
    get_inference_provider,
    get_model_metadata_path,
    get_model_path,
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
        provider = get_inference_provider()

        if provider == "local":
            self.predictor = self._create_local_predictor()
        else:
            self.predictor = self._create_huggingface_predictor()

    def _create_local_predictor(self) -> MovePredictor:
        """Create the local PyTorch policy predictor."""

        from chess_ml.artifacts import (
            load_model_metadata,
            validate_model_metadata,
        )
        from chess_ml.local_inference import LocalPolicyPredictor

        metadata = load_model_metadata(get_model_metadata_path())

        validate_model_metadata(metadata)

        return LocalPolicyPredictor(
            get_model_path(),
            model_version=metadata.model_version,
        )

    def _create_huggingface_predictor(self) -> MovePredictor:
        """Create the Hugging Face policy predictor."""

        from chess_ml.hf_inference import HuggingFacePolicyPredictor

        return HuggingFacePolicyPredictor(
            get_hf_inference_endpoint(),
            token=get_hf_token(),
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
