"""Tests for the ML-backed chess player service."""

from __future__ import annotations

from pathlib import Path

import chess
from backend.services.ml_player import (
    MLPlayer,
    MoveProposal,
)


def test_ml_player_returns_move_proposal(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "ML_MODEL_PATH",
        str(Path(__file__).resolve().parents[2] / "ml" / "artifacts" / "policy_v1.pt"),
    )
    monkeypatch.setenv(
        "ML_MODEL_METADATA_PATH",
        str(
            Path(__file__).resolve().parents[2] / "ml" / "artifacts" / "policy_v1.json"
        ),
    )

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
