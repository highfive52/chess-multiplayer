"""Tests for supervised chess training-data construction."""

import chess
import pytest

from chess_ml.dataset import iter_training_examples


@pytest.fixture
def game_record() -> dict[str, object]:
    return {
        "Site": "https://lichess.org/test-game",
        "WhiteElo": 1900,
        "BlackElo": 1850,
        "Result": "1-0",
        "movetext": (
            "1. e4 e5 "
            "2. Nf3 Nc6 "
            "3. Bb5 a6 "
            "4. Ba4 Nf6"
        ),
    }


def test_one_example_per_ply(game_record):
    examples = list(iter_training_examples(game_record))

    assert len(examples) == 8


def test_first_board_is_starting_position(game_record):
    examples = list(iter_training_examples(game_record))

    assert examples[0].board.fen() == chess.Board().fen()


def test_target_move_is_legal_from_stored_board(game_record):
    examples = list(iter_training_examples(game_record))

    assert all(
        example.move in example.board.legal_moves
        for example in examples
    )


def test_board_is_captured_before_move(game_record):
    examples = list(iter_training_examples(game_record))

    first_example = examples[0]

    assert first_example.move.uci() == "e2e4"

    assert first_example.board.piece_at(
        chess.E2
    ) == chess.Piece(
        chess.PAWN,
        chess.WHITE,
    )

    assert first_example.board.piece_at(chess.E4) is None


def test_ply_sequence_is_contiguous(game_record):
    examples = list(iter_training_examples(game_record))

    assert [
        example.ply
        for example in examples
    ] == list(range(1, 9))


def test_metadata_is_preserved(game_record):
    examples = list(iter_training_examples(game_record))

    assert all(
        example.source_game_id == "https://lichess.org/test-game"
        for example in examples
    )

    assert all(
        example.white_elo == 1900
        for example in examples
    )

    assert all(
        example.black_elo == 1850
        for example in examples
    )


def test_board_snapshots_are_independent(game_record):
    examples = list(iter_training_examples(game_record))

    assert examples[0].board is not examples[1].board

    first_fen = examples[0].board.fen()
    second_fen = examples[1].board.fen()

    examples[0].board.push(examples[0].move)

    assert examples[0].board.fen() != first_fen
    assert examples[1].board.fen() == second_fen


def test_sequential_board_transitions_are_correct(game_record):
    examples = list(iter_training_examples(game_record))

    for current_example, next_example in zip(
        examples,
        examples[1:],
    ):
        board = current_example.board.copy(stack=False)
        board.push(current_example.move)

        assert board.fen() == next_example.board.fen()


def test_illegal_partial_pgn_is_rejected(game_record):
    malformed_record = dict(game_record)

    malformed_record["movetext"] = (
        "1. e4 e5 "
        "2. Nf3 Nc6 "
        "3. Bb5 Kd7"
    )

    with pytest.raises(
        ValueError,
        match="PGN contains parsing errors",
    ):
        list(iter_training_examples(malformed_record))