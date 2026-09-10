"""Bot move generation from authoritative game state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.services.chess_notation import board_from_authoritative
from backend.services.ml_player import MLPlayer


@dataclass(frozen=True)
class BotMove:
    """Backend-coordinate move proposed by an automated player."""

    from_row: int
    from_col: int
    to_row: int
    to_col: int
    promotion: str | None


def square_to_coords(square: str) -> tuple[int, int]:
    """Convert an algebraic square such as e2 to backend row/column coordinates."""

    if len(square) != 2:
        raise ValueError(f"Invalid chess square: {square}")

    file_name = square[0]
    rank_name = square[1]

    if file_name not in "abcdefgh":
        raise ValueError(f"Invalid chess file: {file_name}")

    if rank_name not in "12345678":
        raise ValueError(f"Invalid chess rank: {rank_name}")

    col = ord(file_name) - ord("a")
    row = 8 - int(rank_name)

    return row, col


def generate_bot_move(
    game_state: dict[str, Any],
    ml_player: MLPlayer,
) -> BotMove:
    """Generate a bot move from authoritative backend game state."""

    board = board_from_authoritative(game_state)

    prediction = ml_player.predict_move(board.fen())

    from_row, from_col = square_to_coords(prediction.from_square)

    to_row, to_col = square_to_coords(prediction.to_square)

    return BotMove(
        from_row=from_row,
        from_col=from_col,
        to_row=to_row,
        to_col=to_col,
        promotion=prediction.promotion,
    )
