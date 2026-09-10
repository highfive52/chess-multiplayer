"""Authoritative chess move execution."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from backend.services.chess_notation import board_from_authoritative
from backend.validator import (
    causes_self_check,
    find_king,
    has_legal_moves,
    is_legal_move,
    is_square_attacked,
)


@dataclass(frozen=True)
class MoveResult:
    """Result of attempting to apply a move to authoritative game state."""

    accepted: bool
    reason: str | None
    game_state: dict[str, Any]
    pre_move_state: dict[str, Any] | None = None


def execute_move(
    game_state: dict[str, Any],
    player_color: str,
    from_row: int,
    from_col: int,
    to_row: int,
    to_col: int,
) -> MoveResult:
    """Validate and apply one move to authoritative game state."""

    if game_state.get("status") == "completed":
        return MoveResult(
            accepted=False,
            reason="The game has already ended.",
            game_state=game_state,
        )

    if player_color != game_state.get("current_turn"):
        return MoveResult(
            accepted=False,
            reason="Not your turn",
            game_state=game_state,
        )

    pre_move_state = {
        "board": copy.deepcopy(game_state["board"]),
        "current_turn": game_state.get("current_turn"),
        "castling_rights": copy.deepcopy(game_state.get("castling_rights", {})),
    }

    if not is_legal_move(
        game_state["board"],
        from_row,
        from_col,
        to_row,
        to_col,
        game_state["castling_rights"],
    ):
        return MoveResult(
            accepted=False,
            reason="Illegal chess movement",
            game_state=game_state,
        )

    if causes_self_check(
        game_state["board"],
        player_color,
        from_row,
        from_col,
        to_row,
        to_col,
        game_state["castling_rights"],
    ):
        return MoveResult(
            accepted=False,
            reason="Move leaves your king in check",
            game_state=game_state,
        )

    opponent_color = "black" if player_color == "white" else "white"

    moving_piece = game_state["board"][from_row][from_col]

    if moving_piece:
        piece_type = moving_piece["type"]
        piece_color = moving_piece["color"]

        if piece_type == "k" and abs(to_col - from_col) == 2:
            home_rank = 7 if piece_color == "w" else 0
            is_kingside = to_col > from_col

            old_rook_col = 7 if is_kingside else 0
            new_rook_col = 5 if is_kingside else 3

            rook_piece = game_state["board"][home_rank][old_rook_col]

            game_state["board"][home_rank][new_rook_col] = rook_piece

            game_state["board"][home_rank][old_rook_col] = None

        rights = game_state["castling_rights"][piece_color]

        if piece_type == "k":
            rights["king_has_moved"] = True

        elif piece_type == "r":
            if from_col == 0:
                rights["a_rook_has_moved"] = True

            elif from_col == 7:
                rights["h_rook_has_moved"] = True

        game_state["board"][to_row][to_col] = moving_piece
        game_state["board"][from_row][from_col] = None

    opponent_king = find_king(
        game_state["board"],
        opponent_color,
    )

    opponent_in_check = is_square_attacked(
        game_state["board"],
        opponent_king[0],
        opponent_king[1],
        player_color,
        game_state["castling_rights"],
    )

    if opponent_in_check:
        game_state["check_status"] = opponent_color

        if not has_legal_moves(
            game_state["board"],
            opponent_color,
            game_state["castling_rights"],
        ):
            game_state["status"] = "completed"
            game_state["winner"] = player_color

    else:
        game_state["check_status"] = None

        if not has_legal_moves(
            game_state["board"],
            opponent_color,
            game_state["castling_rights"],
        ):
            game_state["status"] = "completed"
            game_state["winner"] = "draw"

    if game_state["status"] == "active":
        game_state["current_turn"] = opponent_color

    return MoveResult(
        accepted=True,
        reason=None,
        game_state=game_state,
        pre_move_state=pre_move_state,
    )


def final_fen(
    game_state: dict[str, Any],
) -> str:
    """Return FEN for the current authoritative game state."""

    auth_state = {
        "board": game_state["board"],
        "current_turn": game_state.get("current_turn"),
        "castling_rights": game_state.get("castling_rights"),
    }

    return board_from_authoritative(auth_state).fen()
