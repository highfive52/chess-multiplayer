"""Tests for the ML-backed chess player service."""

from __future__ import annotations

import chess
from services.inference import MovePrediction
from services.ml_player import (
    MLPlayer,
    MoveProposal,
)


class FakePredictor:
    def __init__(self, onnx_path, metadata_path):
        self.onnx_path = onnx_path
        self.metadata_path = metadata_path

    def predict(self, fen: str) -> MovePrediction:
        return MovePrediction(
            from_square="e2",
            to_square="e4",
            promotion=None,
            score=0.75,
            model_version="test-model",
        )


def test_ml_player_returns_move_proposal(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "ML_MODEL_ONNX_PATH",
        "artifacts/policy_v1.onnx",
    )
    monkeypatch.setenv(
        "ML_MODEL_METADATA_PATH",
        "artifacts/policy_v1.json",
    )
    monkeypatch.setattr("services.ml_player.ONNXPolicyPredictor", FakePredictor)

    player = MLPlayer()

    proposal = player.predict_move(chess.STARTING_FEN)

    assert isinstance(
        proposal,
        MoveProposal,
    )

    assert proposal.from_square in chess.SQUARE_NAMES
    assert proposal.to_square in chess.SQUARE_NAMES

    assert proposal.promotion in {
        None,
        "knight",
        "bishop",
        "rook",
        "queen",
    }
