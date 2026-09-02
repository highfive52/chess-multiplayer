from backend.services.chess_notation import (
    board_from_fen,
    apply_move_and_fen,
    coords_to_square,
)


def test_coords_to_square():
    assert coords_to_square((7, 0)) == "a1"
    assert coords_to_square((0, 4)) == "e8"


def test_apply_move_and_fen_simple_pawn_move():
    board = board_from_fen(None)
    san, fen_after = apply_move_and_fen(board, "e2", "e4")
    assert san == "e4"
    # ensure FEN reflects white pawn on e4 (rank 4 -> '4P3' segment)
    assert "4P3" in fen_after or "4p3" in fen_after


def test_apply_move_with_tuple_coords_and_promotion():
    # Setup a board where promotion is legal: place a white pawn on 7th rank
    # We'll construct a FEN with a white pawn on a7 (row 1 in our coords -> a7)
    # FEN for a position with white pawn on a7 ready to promote and black king elsewhere
    fen = "8/P7/8/8/8/8/8/4k2K w - - 0 1"
    board = board_from_fen(fen)
    # pawn from a7 (row 1, col 0) to a8 (row 0, col 0) promote to queen
    san, fen_after = apply_move_and_fen(board, (1, 0), (0, 0), promotion="q")
    assert "=Q" in san or san.endswith("Q")
    assert "Q" in fen_after or "q" in fen_after
