"""Tests for standalone chess policy inference."""

from pathlib import Path

import chess
import torch

from chess_ml.inference import (
    MovePrediction,
    PolicyPredictor,
)


MODEL_PATH = Path(
    __file__
).parents[1] / "artifacts" / "policy_v1.pt"


def test_policy_predictor_returns_move_prediction():
    predictor = PolicyPredictor(
        MODEL_PATH,
        model_version="policy-v1",
        device=torch.device("cpu"),
    )

    prediction = predictor.predict(
        chess.STARTING_FEN
    )

    assert isinstance(
        prediction,
        MovePrediction,
    )

    assert prediction.from_square in chess.SQUARE_NAMES
    assert prediction.to_square in chess.SQUARE_NAMES

    assert prediction.promotion in {
        None,
        "knight",
        "bishop",
        "rook",
        "queen",
    }

    assert 0.0 <= prediction.score <= 1.0

    assert (
        prediction.model_version
        == "policy-v1"
    )

def test_policy_predictor_handles_smoke_test_positions():
    predictor = PolicyPredictor(
        MODEL_PATH,
        model_version="policy-v1",
        device=torch.device("cpu"),
    )

    after_e4 = chess.Board()
    after_e4.push_uci("e2e4")

    after_e4_e5 = chess.Board()
    after_e4_e5.push_uci("e2e4")
    after_e4_e5.push_uci("e7e5")

    positions = [
        chess.STARTING_FEN,
        after_e4.fen(),
        after_e4_e5.fen(),
        (
            "r1bq1rk1/pp2bppp/2n1pn2/2pp4/"
            "3P4/2PBPN2/PP1NBPPP/R2Q1RK1 w - - 2 9"
        ),
        (
            "8/5pk1/6p1/8/4P3/5K2/8/8 w - - 0 1"
        ),
    ]

    for fen in positions:
        prediction = predictor.predict(fen)

        assert isinstance(
            prediction,
            MovePrediction,
        )