"""Local PyTorch inference for the chess policy model."""

from __future__ import annotations

from pathlib import Path

import chess
import torch
from encoding import encode_board
from moves import decode_move

from chess_ml.inference import MovePrediction
from chess_ml.model import PolicyCNN


def predict_move(
    fen: str,
    *,
    model: PolicyCNN,
    device: torch.device,
    model_version: str,
) -> MovePrediction:
    """Predict one move from a FEN position using a local PyTorch model."""

    board = chess.Board(fen)

    x = encode_board(board)

    x = x.unsqueeze(0).to(device)

    model.eval()

    with torch.no_grad():
        logits = model(x)

        probabilities = torch.softmax(
            logits,
            dim=1,
        )

    predicted_id = int(logits.argmax(dim=1).item())

    predicted_move = decode_move(predicted_id)

    score = float(
        probabilities[
            0,
            predicted_id,
        ].item()
    )

    return MovePrediction(
        from_square=chess.square_name(predicted_move.from_square),
        to_square=chess.square_name(predicted_move.to_square),
        promotion=(
            chess.piece_name(predicted_move.promotion)
            if predicted_move.promotion is not None
            else None
        ),
        score=score,
        model_version=model_version,
    )


class LocalPolicyPredictor:
    """Load and reuse a local PyTorch chess policy model."""

    def __init__(
        self,
        model_path: str | Path,
        *,
        model_version: str,
        device: torch.device | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        self.model_version = model_version

        self.device = (
            device
            if device is not None
            else torch.device("cuda" if torch.cuda.is_available() else "cpu")
        )

        self.model = PolicyCNN().to(self.device)

        state_dict = torch.load(
            self.model_path,
            map_location=self.device,
        )

        self.model.load_state_dict(state_dict)

        self.model.eval()

    def predict(
        self,
        fen: str,
    ) -> MovePrediction:
        """Predict one move from a FEN position."""

        return predict_move(
            fen,
            model=self.model,
            device=self.device,
            model_version=self.model_version,
        )
