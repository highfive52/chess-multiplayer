"""Chess notation adapter using python-chess.

This module provides a small boundary between the application's authoritative
board representation and `python-chess` for SAN and FEN generation.

Design notes:
- `board_from_fen(fen)` constructs a `chess.Board` from a FEN string.
- `coords_to_square((row,col))` converts a numeric board coordinate to
  algebraic notation. It assumes `row` 0 is the top (rank 8) and `row` 7 is
  the bottom (rank 1), matching common 2D array board representations.
- `move_to_san` and `apply_move_and_fen` accept either algebraic square
  strings (e.g. 'e2') or numeric `(row,col)` tuples.
"""

from typing import Tuple, Optional, Union

import chess

SquareInput = Union[str, Tuple[int, int]]


def board_from_fen(fen: Optional[str]) -> chess.Board:
    """Return a `chess.Board` for the given FEN.

    If `fen` is None or the special value 'startpos', returns the standard
    starting position.
    """
    if not fen or fen == "startpos":
        return chess.Board()
    return chess.Board(fen=fen)


def coords_to_square(coord: Tuple[int, int]) -> str:
    """Convert (row, col) -> algebraic square string.

    Assumes row 0 maps to rank 8 and row 7 maps to rank 1.
    """
    row, col = coord
    if not (0 <= row <= 7 and 0 <= col <= 7):
        raise ValueError("board coordinates must be in range 0..7")
    file_char = chr(ord("a") + col)
    rank_char = str(8 - row)
    return f"{file_char}{rank_char}"


def _to_algebraic(sq: SquareInput) -> str:
    if isinstance(sq, str):
        return sq
    return coords_to_square(sq)


def _make_uci(
    from_sq: SquareInput, to_sq: SquareInput, promotion: Optional[str]
) -> str:
    f = _to_algebraic(from_sq)
    t = _to_algebraic(to_sq)
    uci = f + t
    if promotion:
        # python-chess expects promotion as single letter, lowercase
        uci += promotion.lower()[0]
    return uci


def move_to_san(
    board: chess.Board,
    from_sq: SquareInput,
    to_sq: SquareInput,
    promotion: Optional[str] = None,
) -> str:
    """Return the SAN for the given move on `board`.

    Raises `ValueError` if the move is illegal.
    """
    uci = _make_uci(from_sq, to_sq, promotion)
    move = chess.Move.from_uci(uci)
    if move not in board.legal_moves:
        raise ValueError("illegal move for the provided board")
    return board.san(move)


def apply_move_and_fen(
    board: chess.Board,
    from_sq: SquareInput,
    to_sq: SquareInput,
    promotion: Optional[str] = None,
) -> Tuple[str, str]:
    """Apply the move to `board` and return (san, fen_after).

    The provided `board` is mutated (consistent with python-chess push semantics).
    """
    uci = _make_uci(from_sq, to_sq, promotion)
    move = chess.Move.from_uci(uci)
    if move not in board.legal_moves:
        raise ValueError("illegal move for the provided board")
    san = board.san(move)
    board.push(move)
    return san, board.fen()


def board_from_authoritative(state: Union[str, dict]) -> chess.Board:
    """Create a `chess.Board` from an authoritative state.

    Supported inputs:
    - FEN string
    - dict with key 'fen'

    For other authoritative representations (e.g. nested arrays), implement a
    conversion function here that maps your internal model to a `chess.Board`.
    """
    if state is None:
        return board_from_fen(None)
    if isinstance(state, str):
        return board_from_fen(state)
    if isinstance(state, dict):
        if "fen" in state:
            return board_from_fen(state["fen"])
        if "board" in state:
            # state contains the application board array and optional metadata
            if state["board"] is None:
                return board_from_fen(None)
            return board_from_app_board(
                state["board"],
                current_turn=state.get("current_turn"),
                castling_rights=state.get("castling_rights"),
            )
    raise NotImplementedError("conversion from authoritative state not implemented")


def board_from_app_board(
    board_array,
    current_turn: Optional[str] = None,
    castling_rights: Optional[dict] = None,
) -> chess.Board:
    """Convert the application's nested board array into a `chess.Board`.

    - `board_array` is expected as an 8x8 list-of-lists where row 0 is rank 8, row 7 is rank 1.
    - Each square is either None or a dict like `{"type": "p","color": "w"}`.
    - `current_turn` may be 'white' or 'black'.
    - `castling_rights` follows the app shape used in `create_initial_state()`.
    """
    # Build piece placement FEN
    ranks = []
    for row in range(0, 8):
        empty = 0
        parts = []
        for col in range(0, 8):
            sq = board_array[row][col]
            if not sq:
                empty += 1
            else:
                if empty:
                    parts.append(str(empty))
                    empty = 0
                ptype = sq.get("type", "?")
                color = sq.get("color", "w")
                char = ptype.lower()
                if color == "w":
                    char = char.upper()
                parts.append(char)
        if empty:
            parts.append(str(empty))
        ranks.append("".join(parts))
    placement = "/".join(ranks)

    # turn
    turn = "w" if (current_turn is None or current_turn == "white") else "b"

    # castling rights
    castle = []
    if castling_rights:
        w = castling_rights.get("w", {})
        b = castling_rights.get("b", {})
        if not w.get("king_has_moved", True):
            if not w.get("h_rook_has_moved", True):
                castle.append("K")
            if not w.get("a_rook_has_moved", True):
                castle.append("Q")
        if not b.get("king_has_moved", True):
            if not b.get("h_rook_has_moved", True):
                castle.append("k")
            if not b.get("a_rook_has_moved", True):
                castle.append("q")
    castling = "".join(castle) if castle else "-"

    full_fen = f"{placement} {turn} {castling} - 0 1"
    return chess.Board(fen=full_fen)
