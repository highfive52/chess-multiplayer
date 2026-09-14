"""Backend ONNX inference for the chess policy model."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import chess
import numpy as np
import onnxruntime as ort
from encoding import encode_board
from moves import MOVE_CLASS_COUNT, decode_move

EXPECTED_MODEL_VERSION = "policy-v1"
EXPECTED_ARCHITECTURE_VERSION = "policy-cnn-v1"
EXPECTED_BOARD_ENCODING_VERSION = "board-v1"
EXPECTED_MOVE_ENCODING_VERSION = "move-v1"


@dataclass(frozen=True)
class MovePrediction:
    """One move prediction produced by the backend runtime."""

    from_square: str
    to_square: str
    promotion: str | None
    score: float
    model_version: str


@dataclass(frozen=True)
class ModelArtifactMetadata:
    """Compatibility metadata for an exported policy artifact."""

    model_version: str
    architecture_version: str
    board_encoding_version: str
    move_encoding_version: str
    move_class_count: int


def load_model_metadata(metadata_path: str | Path) -> ModelArtifactMetadata:
    """Load model metadata from the local JSON artifact."""

    path = Path(metadata_path)

    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    return ModelArtifactMetadata(
        model_version=payload["model_version"],
        architecture_version=payload["architecture_version"],
        board_encoding_version=payload["board_encoding_version"],
        move_encoding_version=payload["move_encoding_version"],
        move_class_count=payload["move_class_count"],
    )


def validate_model_metadata(metadata: ModelArtifactMetadata) -> None:
    """Validate compatibility with the backend runtime."""

    expected = {
        "model_version": EXPECTED_MODEL_VERSION,
        "architecture_version": EXPECTED_ARCHITECTURE_VERSION,
        "board_encoding_version": EXPECTED_BOARD_ENCODING_VERSION,
        "move_encoding_version": EXPECTED_MOVE_ENCODING_VERSION,
        "move_class_count": MOVE_CLASS_COUNT,
    }

    actual = {
        "model_version": metadata.model_version,
        "architecture_version": metadata.architecture_version,
        "board_encoding_version": metadata.board_encoding_version,
        "move_encoding_version": metadata.move_encoding_version,
        "move_class_count": metadata.move_class_count,
    }

    mismatches = {
        key: (
            expected[key],
            actual[key],
        )
        for key in expected
        if expected[key] != actual[key]
    }

    if mismatches:
        details = ", ".join(
            f"{key}: expected {expected_value!r}, got {actual_value!r}"
            for key, (
                expected_value,
                actual_value,
            ) in mismatches.items()
        )

        raise RuntimeError(f"Incompatible model artifact metadata: {details}")


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits)
    exp_logits = np.exp(shifted)
    return exp_logits / exp_logits.sum()


class ONNXPolicyPredictor:
    """Load and reuse an exported ONNX chess policy model."""

    def __init__(
        self,
        onnx_path: str | Path,
        metadata_path: str | Path,
    ) -> None:
        self.onnx_path = Path(onnx_path)

        metadata = load_model_metadata(metadata_path)
        validate_model_metadata(metadata)

        self.model_version = metadata.model_version
        self.session = ort.InferenceSession(str(self.onnx_path))

    def predict(self, fen: str) -> MovePrediction:
        """Predict one move from a FEN position."""

        board = chess.Board(fen)

        board_tensor = encode_board(board).unsqueeze(0).cpu().numpy()

        logits = self.session.run(
            None,
            {"board": board_tensor},
        )[0]

        logits_row = np.asarray(logits, dtype=np.float32)[0]
        probabilities = _softmax(logits_row)

        predicted_id = int(np.argmax(logits_row))
        predicted_move = decode_move(predicted_id)

        return MovePrediction(
            from_square=chess.square_name(predicted_move.from_square),
            to_square=chess.square_name(predicted_move.to_square),
            promotion=(
                chess.piece_name(predicted_move.promotion)
                if predicted_move.promotion is not None
                else None
            ),
            score=float(probabilities[predicted_id]),
            model_version=self.model_version,
        )
