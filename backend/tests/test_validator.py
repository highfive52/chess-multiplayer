import copy

from backend.validator import (
    is_legal_move,
    causes_self_check,
    has_legal_moves,
)
from backend.main import create_initial_board


def test_knight_move_from_start_is_valid():
    board = create_initial_board()
    # White knight at b1 -> (7,1) can move to c3 -> (5,2)
    assert is_legal_move(board, 7, 1, 5, 2) is True


def test_pawn_double_move_allowed_and_blocked():
    board = create_initial_board()
    # White pawn at a2 -> (6,0) double-move to (4,0)
    assert is_legal_move(board, 6, 0, 4, 0) is True

    # Block intermediate square to prevent double move
    blocked = copy.deepcopy(board)
    blocked[5][0] = {"type": "n", "color": "b"}
    assert is_legal_move(blocked, 6, 0, 4, 0) is False


def test_rook_blocked_by_pawn_and_cannot_capture_own():
    board = create_initial_board()
    # White rook at a1 (7,0) can't jump to a4 (4,0) because pawns block
    assert is_legal_move(board, 7, 0, 4, 0) is False

    # Attempt to capture own pawn at a2 (6,0)
    assert is_legal_move(board, 7, 0, 6, 0) is False


def test_out_of_bounds_move_rejected():
    board = create_initial_board()
    assert is_legal_move(board, 7, 0, 8, 0) is False
    assert is_legal_move(board, -1, 0, 0, 0) is False


def test_causes_self_check_detection():
    # Build a minimal board where moving a blocking rook exposes the king
    board = [[None for _ in range(8)] for _ in range(8)]
    # White king at (0,0)
    board[0][0] = {"type": "k", "color": "w"}
    # White rook blocking at (0,1)
    board[0][1] = {"type": "r", "color": "w"}
    # Black rook aiming at the file at (0,3)
    board[0][3] = {"type": "r", "color": "b"}

    # If white rook moves away from (0,1) the king at (0,0) becomes attacked
    assert causes_self_check(board, "white", 0, 1, 1, 1) is True


def test_has_legal_moves_on_initial_board():
    board = create_initial_board()
    assert has_legal_moves(board, "white") is True
