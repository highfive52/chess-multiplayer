"""Tests for chess move encoding."""

import chess
import pytest
from chess_ml.moves import (
    BASE_MOVE_COUNT,
    MOVE_CLASS_COUNT,
    decode_move,
    encode_move,
)


def test_encode_ordinary_move():
    move = chess.Move.from_uci("g1f3")

    move_id = encode_move(move)

    expected = chess.G1 * 64 + chess.F3

    assert move_id == expected


def test_decode_ordinary_move():
    move = chess.Move.from_uci("g1f3")

    move_id = encode_move(move)
    decoded = decode_move(move_id)

    assert decoded == move


def test_ordinary_move_round_trip():
    moves = [
        chess.Move.from_uci("e2e4"),
        chess.Move.from_uci("g1f3"),
        chess.Move.from_uci("b8c6"),
        chess.Move.from_uci("d1h5"),
    ]

    for move in moves:
        assert decode_move(encode_move(move)) == move


def test_different_moves_have_different_ids():
    first = chess.Move.from_uci("g1f3")
    second = chess.Move.from_uci("g1h3")
    third = chess.Move.from_uci("b1c3")

    move_ids = {
        encode_move(first),
        encode_move(second),
        encode_move(third),
    }

    assert len(move_ids) == 3


def test_promotion_moves_have_distinct_ids():
    knight = chess.Move.from_uci("e7e8n")
    bishop = chess.Move.from_uci("e7e8b")
    rook = chess.Move.from_uci("e7e8r")
    queen = chess.Move.from_uci("e7e8q")

    move_ids = {
        encode_move(knight),
        encode_move(bishop),
        encode_move(rook),
        encode_move(queen),
    }

    assert len(move_ids) == 4


def test_promotion_moves_use_separate_class_blocks():
    normal = chess.Move.from_uci("e7e8")
    knight = chess.Move.from_uci("e7e8n")
    bishop = chess.Move.from_uci("e7e8b")
    rook = chess.Move.from_uci("e7e8r")
    queen = chess.Move.from_uci("e7e8q")

    normal_id = encode_move(normal)

    assert encode_move(knight) == normal_id + BASE_MOVE_COUNT
    assert encode_move(bishop) == normal_id + (2 * BASE_MOVE_COUNT)
    assert encode_move(rook) == normal_id + (3 * BASE_MOVE_COUNT)
    assert encode_move(queen) == normal_id + (4 * BASE_MOVE_COUNT)


def test_promotion_round_trip():
    moves = [
        chess.Move.from_uci("e7e8n"),
        chess.Move.from_uci("e7e8b"),
        chess.Move.from_uci("e7e8r"),
        chess.Move.from_uci("e7e8q"),
    ]

    for move in moves:
        assert decode_move(encode_move(move)) == move


def test_black_promotion_round_trip():
    moves = [
        chess.Move.from_uci("a2a1n"),
        chess.Move.from_uci("a2a1b"),
        chess.Move.from_uci("a2a1r"),
        chess.Move.from_uci("a2a1q"),
    ]

    for move in moves:
        assert decode_move(encode_move(move)) == move


def test_castling_moves_round_trip():
    moves = [
        chess.Move.from_uci("e1g1"),
        chess.Move.from_uci("e1c1"),
        chess.Move.from_uci("e8g8"),
        chess.Move.from_uci("e8c8"),
    ]

    for move in moves:
        assert decode_move(encode_move(move)) == move


def test_en_passant_move_round_trip():
    move = chess.Move.from_uci("e5d6")

    assert decode_move(encode_move(move)) == move


def test_encoded_move_is_within_class_range():
    moves = [
        chess.Move.from_uci("a1a2"),
        chess.Move.from_uci("h8h7"),
        chess.Move.from_uci("e2e4"),
        chess.Move.from_uci("a7a8q"),
    ]

    for move in moves:
        move_id = encode_move(move)

        assert 0 <= move_id < MOVE_CLASS_COUNT


def test_lowest_move_id_decodes():
    move = decode_move(0)

    assert move.from_square == chess.A1
    assert move.to_square == chess.A1
    assert move.promotion is None


def test_highest_move_id_decodes():
    move = decode_move(MOVE_CLASS_COUNT - 1)

    assert move.from_square == chess.H8
    assert move.to_square == chess.H8
    assert move.promotion == chess.QUEEN


def test_negative_move_id_is_rejected():
    with pytest.raises(
        ValueError,
        match="Move ID must be between",
    ):
        decode_move(-1)


def test_move_id_above_range_is_rejected():
    with pytest.raises(
        ValueError,
        match="Move ID must be between",
    ):
        decode_move(MOVE_CLASS_COUNT)


def test_unsupported_promotion_piece_is_rejected():
    move = chess.Move(
        from_square=chess.E7,
        to_square=chess.E8,
        promotion=chess.KING,
    )

    with pytest.raises(
        ValueError,
        match="Unsupported promotion piece",
    ):
        encode_move(move)


def test_encoding_is_deterministic():
    move = chess.Move.from_uci("g1f3")

    first = encode_move(move)
    second = encode_move(move)

    assert first == second
