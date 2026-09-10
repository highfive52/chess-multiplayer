"""Tests for chess board tensor encoding."""

import chess
import torch

from chess_ml.encoding import encode_board


def test_starting_position_tensor_shape_and_dtype():
    board = chess.Board()

    tensor = encode_board(board)

    assert tensor.shape == (18, 8, 8)
    assert tensor.dtype == torch.float32


def test_starting_position_piece_count():
    board = chess.Board()

    tensor = encode_board(board)

    assert tensor[:12].sum().item() == 32.0


def test_starting_position_white_pawns():
    board = chess.Board()

    tensor = encode_board(board)

    white_pawn_channel = tensor[0]

    for file in range(8):
        assert white_pawn_channel[1, file] == 1.0

    assert white_pawn_channel.sum().item() == 8.0


def test_starting_position_white_knights():
    board = chess.Board()

    tensor = encode_board(board)

    white_knight_channel = tensor[1]

    assert white_knight_channel[
        chess.square_rank(chess.B1),
        chess.square_file(chess.B1),
    ] == 1.0

    assert white_knight_channel[
        chess.square_rank(chess.G1),
        chess.square_file(chess.G1),
    ] == 1.0

    assert white_knight_channel.sum().item() == 2.0


def test_starting_position_white_bishops():
    board = chess.Board()

    tensor = encode_board(board)

    white_bishop_channel = tensor[2]

    assert white_bishop_channel[
        chess.square_rank(chess.C1),
        chess.square_file(chess.C1),
    ] == 1.0

    assert white_bishop_channel[
        chess.square_rank(chess.F1),
        chess.square_file(chess.F1),
    ] == 1.0

    assert white_bishop_channel.sum().item() == 2.0


def test_starting_position_white_rooks():
    board = chess.Board()

    tensor = encode_board(board)

    white_rook_channel = tensor[3]

    assert white_rook_channel[
        chess.square_rank(chess.A1),
        chess.square_file(chess.A1),
    ] == 1.0

    assert white_rook_channel[
        chess.square_rank(chess.H1),
        chess.square_file(chess.H1),
    ] == 1.0

    assert white_rook_channel.sum().item() == 2.0


def test_starting_position_white_queen():
    board = chess.Board()

    tensor = encode_board(board)

    white_queen_channel = tensor[4]

    assert white_queen_channel[
        chess.square_rank(chess.D1),
        chess.square_file(chess.D1),
    ] == 1.0

    assert white_queen_channel.sum().item() == 1.0


def test_starting_position_white_king():
    board = chess.Board()

    tensor = encode_board(board)

    white_king_channel = tensor[5]

    assert white_king_channel[
        chess.square_rank(chess.E1),
        chess.square_file(chess.E1),
    ] == 1.0

    assert white_king_channel.sum().item() == 1.0


def test_starting_position_black_pieces():
    board = chess.Board()

    tensor = encode_board(board)

    assert tensor[6, 6].sum().item() == 8.0

    assert tensor[
        7,
        chess.square_rank(chess.B8),
        chess.square_file(chess.B8),
    ] == 1.0

    assert tensor[
        7,
        chess.square_rank(chess.G8),
        chess.square_file(chess.G8),
    ] == 1.0

    assert tensor[
        8,
        chess.square_rank(chess.C8),
        chess.square_file(chess.C8),
    ] == 1.0

    assert tensor[
        8,
        chess.square_rank(chess.F8),
        chess.square_file(chess.F8),
    ] == 1.0

    assert tensor[
        9,
        chess.square_rank(chess.A8),
        chess.square_file(chess.A8),
    ] == 1.0

    assert tensor[
        9,
        chess.square_rank(chess.H8),
        chess.square_file(chess.H8),
    ] == 1.0

    assert tensor[
        10,
        chess.square_rank(chess.D8),
        chess.square_file(chess.D8),
    ] == 1.0

    assert tensor[
        11,
        chess.square_rank(chess.E8),
        chess.square_file(chess.E8),
    ] == 1.0

    assert tensor[7].sum().item() == 2.0
    assert tensor[8].sum().item() == 2.0
    assert tensor[9].sum().item() == 2.0
    assert tensor[10].sum().item() == 1.0
    assert tensor[11].sum().item() == 1.0


def test_starting_position_side_to_move():
    board = chess.Board()

    tensor = encode_board(board)

    assert torch.all(tensor[12] == 1.0)


def test_starting_position_castling_rights():
    board = chess.Board()

    tensor = encode_board(board)

    assert torch.all(tensor[13] == 1.0)
    assert torch.all(tensor[14] == 1.0)
    assert torch.all(tensor[15] == 1.0)
    assert torch.all(tensor[16] == 1.0)


def test_starting_position_has_no_en_passant_target():
    board = chess.Board()

    tensor = encode_board(board)

    assert tensor[17].sum().item() == 0.0

#------

def test_position_after_e4():
    board = chess.Board()
    board.push_uci("e2e4")

    tensor = encode_board(board)

    # White pawn moved from e2 to e4.
    assert tensor[
        0,
        chess.square_rank(chess.E2),
        chess.square_file(chess.E2),
    ] == 0.0

    assert tensor[
        0,
        chess.square_rank(chess.E4),
        chess.square_file(chess.E4),
    ] == 1.0

    # Black is now to move.
    assert torch.all(tensor[12] == 0.0)

    # Castling rights are unchanged.
    assert torch.all(tensor[13] == 1.0)
    assert torch.all(tensor[14] == 1.0)
    assert torch.all(tensor[15] == 1.0)
    assert torch.all(tensor[16] == 1.0)

    # e3 is the en-passant target square.
    assert tensor[
        17,
        chess.square_rank(chess.E3),
        chess.square_file(chess.E3),
    ] == 1.0

    assert tensor[17].sum().item() == 1.0


def test_position_after_e4_e5_nf3():
    board = chess.Board()

    board.push_uci("e2e4")
    board.push_uci("e7e5")
    board.push_uci("g1f3")

    tensor = encode_board(board)

    # White pawn is on e4.
    assert tensor[
        0,
        chess.square_rank(chess.E4),
        chess.square_file(chess.E4),
    ] == 1.0

    assert tensor[
        0,
        chess.square_rank(chess.E2),
        chess.square_file(chess.E2),
    ] == 0.0

    # Black pawn is on e5.
    assert tensor[
        6,
        chess.square_rank(chess.E5),
        chess.square_file(chess.E5),
    ] == 1.0

    assert tensor[
        6,
        chess.square_rank(chess.E7),
        chess.square_file(chess.E7),
    ] == 0.0

    # White knight moved from g1 to f3.
    assert tensor[
        1,
        chess.square_rank(chess.G1),
        chess.square_file(chess.G1),
    ] == 0.0

    assert tensor[
        1,
        chess.square_rank(chess.F3),
        chess.square_file(chess.F3),
    ] == 1.0

    # Black is to move.
    assert torch.all(tensor[12] == 0.0)

    # No en-passant target remains after Nf3.
    assert tensor[17].sum().item() == 0.0


def test_white_kingside_castling_right_is_removed_after_king_move():
    board = chess.Board()

    board.push_uci("e2e4")
    board.push_uci("e7e5")
    board.push_uci("e1e2")

    tensor = encode_board(board)

    assert torch.all(tensor[13] == 0.0)
    assert torch.all(tensor[14] == 0.0)

    assert torch.all(tensor[15] == 1.0)
    assert torch.all(tensor[16] == 1.0)


def test_white_kingside_castling_right_is_removed_after_rook_move():
    board = chess.Board()

    board.push_uci("h2h4")
    board.push_uci("a7a6")
    board.push_uci("h1h3")

    tensor = encode_board(board)

    assert torch.all(tensor[13] == 0.0)
    assert torch.all(tensor[14] == 1.0)

    assert torch.all(tensor[15] == 1.0)
    assert torch.all(tensor[16] == 1.0)


def test_en_passant_target_square_is_encoded():
    board = chess.Board()

    board.push_uci("e2e4")

    tensor = encode_board(board)

    assert board.ep_square == chess.E3

    assert tensor[
        17,
        chess.square_rank(chess.E3),
        chess.square_file(chess.E3),
    ] == 1.0

    assert tensor[17].sum().item() == 1.0


def test_en_passant_target_is_cleared_after_next_move():
    board = chess.Board()

    board.push_uci("e2e4")
    board.push_uci("g8f6")

    tensor = encode_board(board)

    assert board.ep_square is None
    assert tensor[17].sum().item() == 0.0


def test_en_passant_capture_position():
    board = chess.Board()

    board.push_uci("e2e4")
    board.push_uci("a7a6")
    board.push_uci("e4e5")
    board.push_uci("d7d5")

    tensor = encode_board(board)

    # White pawn is on e5.
    assert tensor[
        0,
        chess.square_rank(chess.E5),
        chess.square_file(chess.E5),
    ] == 1.0

    # Black pawn is on d5.
    assert tensor[
        6,
        chess.square_rank(chess.D5),
        chess.square_file(chess.D5),
    ] == 1.0

    # d6 is the en-passant target.
    assert board.ep_square == chess.D6

    assert tensor[
        17,
        chess.square_rank(chess.D6),
        chess.square_file(chess.D6),
    ] == 1.0

    assert tensor[17].sum().item() == 1.0


def test_promotion_to_queen_is_encoded():
    board = chess.Board(
        "8/P7/8/8/8/8/7p/4K2k w - - 0 1"
    )

    board.push_uci("a7a8q")

    tensor = encode_board(board)

    # Pawn is no longer on a7.
    assert tensor[
        0,
        chess.square_rank(chess.A7),
        chess.square_file(chess.A7),
    ] == 0.0

    # No white pawn remains on a8.
    assert tensor[
        0,
        chess.square_rank(chess.A8),
        chess.square_file(chess.A8),
    ] == 0.0

    # Promoted white queen is on a8.
    assert tensor[
        4,
        chess.square_rank(chess.A8),
        chess.square_file(chess.A8),
    ] == 1.0

    assert tensor[4].sum().item() == 1.0


def test_tensor_contains_only_binary_values():
    board = chess.Board()

    tensor = encode_board(board)

    assert torch.all(
        (tensor == 0.0)
        | (tensor == 1.0)
    )


def test_encoding_is_deterministic():
    board = chess.Board()

    board.push_uci("e2e4")
    board.push_uci("e7e5")
    board.push_uci("g1f3")

    first = encode_board(board)
    second = encode_board(board)

    assert torch.equal(first, second)


def test_encoding_does_not_mutate_board():
    board = chess.Board()

    board.push_uci("e2e4")

    fen_before = board.fen()

    encode_board(board)

    assert board.fen() == fen_before