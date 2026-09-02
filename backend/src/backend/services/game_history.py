"""Service to record game history by coordinating repositories and notation adapter.

Functions:
- `create_game_record(room_code, initial_fen, source_type)` -> creates a `games` row.
- `record_move(game_id, authoritative_state, from_sq, to_sq, promotion)` -> computes SAN/FEN, determines ply, and inserts move.
- `complete_game(game_id, result, final_fen)` -> marks game completed.
"""

from typing import Optional, Union, Dict

from ..services.chess_notation import (
    board_from_authoritative,
    apply_move_and_fen,
    coords_to_square,
)
from ..repositories import games as games_repo
from ..repositories import game_moves as moves_repo
from ..repositories.game_moves import DuplicateMoveError


def _to_algebraic(sq: Union[str, tuple]) -> str:
    if isinstance(sq, str):
        return sq
    return coords_to_square(sq)


def create_game_record(
    room_code: Optional[str], initial_fen: Optional[str], source_type: str = "live"
) -> str:
    """Create a game record and return its id."""
    if initial_fen is None:
        initial_fen = "startpos"
    return games_repo.create_game(room_code, initial_fen, source_type)


def record_move(
    game_id: str,
    authoritative_state: Union[str, dict, None],
    from_sq: Union[str, tuple],
    to_sq: Union[str, tuple],
    promotion: Optional[str] = None,
) -> Dict:
    """Record a single move for `game_id`.

    - Builds a `chess.Board` from `authoritative_state` (FEN or dict with 'fen').
    - Computes SAN and resulting FEN after applying the move.
    - Computes next `ply` by counting existing moves and inserts the move.

    Returns a dict with `id`, `ply`, `san`, and `fen_after`.
    If the move already exists (idempotent), returns the existing move record.
    """
    # validate game exists
    game = games_repo.get_game(game_id)
    if not game:
        raise ValueError("game not found")

    board = board_from_authoritative(authoritative_state)
    san, fen_after = apply_move_and_fen(board, from_sq, to_sq, promotion)

    # Attempt to insert without computing ply client-side; the repository will
    # compute the next ply atomically when `ply` is None.
    try:
        move_id = moves_repo.insert_move(
            game_id,
            None,
            san,
            fen_after,
            from_square=_to_algebraic(from_sq),
            to_square=_to_algebraic(to_sq),
            promotion=promotion,
        )
        # Query the inserted move to include the ply in the result
        mv = moves_repo.get_move_by_id(move_id)
        if mv:
            return {
                "id": move_id,
                "ply": mv.get("ply"),
                "san": san,
                "fen_after": fen_after,
            }
        # Fallback: return without ply
        return {"id": move_id, "ply": None, "san": san, "fen_after": fen_after}
    except DuplicateMoveError:
        # Return the matching move when a retry races with an existing insert.
        expected_from = _to_algebraic(from_sq)
        expected_to = _to_algebraic(to_sq)
        moves = moves_repo.get_moves_for_game(game_id)
        for move in moves:
            if (
                move.get("san") == san
                and move.get("from_square") in (None, expected_from)
                and move.get("to_square") in (None, expected_to)
            ):
                return {
                    "id": move.get("id"),
                    "ply": move.get("ply"),
                    "san": move.get("san"),
                    "fen_after": move.get("fen_after"),
                }
        raise


def complete_game(
    game_id: str, result: Optional[str], final_fen: Optional[str]
) -> None:
    games_repo.complete_game(game_id, result, final_fen)
