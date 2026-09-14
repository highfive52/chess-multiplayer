"""Tests for supervised chess training-data construction."""

from itertools import pairwise

import chess
import pytest
import torch
from chess_ml.dataset import (
    ChessPolicyDataset,
    build_training_examples,
    iter_training_examples,
    split_game_records,
)
from chess_ml.moves import encode_move
from torch.utils.data import DataLoader


@pytest.fixture
def game_record() -> dict[str, object]:
    return {
        "Site": "https://lichess.org/test-game",
        "WhiteElo": 1900,
        "BlackElo": 1850,
        "Result": "1-0",
        "movetext": ("1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6"),
    }


def test_one_example_per_ply(game_record):
    examples = list(iter_training_examples(game_record))

    assert len(examples) == 8


def test_first_board_is_starting_position(game_record):
    examples = list(iter_training_examples(game_record))

    assert examples[0].board.fen() == chess.Board().fen()


def test_target_move_is_legal_from_stored_board(game_record):
    examples = list(iter_training_examples(game_record))

    assert all(example.move in example.board.legal_moves for example in examples)


def test_board_is_captured_before_move(game_record):
    examples = list(iter_training_examples(game_record))

    first_example = examples[0]

    assert first_example.move.uci() == "e2e4"

    assert first_example.board.piece_at(chess.E2) == chess.Piece(
        chess.PAWN,
        chess.WHITE,
    )

    assert first_example.board.piece_at(chess.E4) is None


def test_ply_sequence_is_contiguous(game_record):
    examples = list(iter_training_examples(game_record))

    assert [example.ply for example in examples] == list(range(1, 9))


def test_metadata_is_preserved(game_record):
    examples = list(iter_training_examples(game_record))

    assert all(
        example.source_game_id == "https://lichess.org/test-game"
        for example in examples
    )

    assert all(example.white_elo == 1900 for example in examples)

    assert all(example.black_elo == 1850 for example in examples)


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

    for current_example, next_example in pairwise(examples):
        board = current_example.board.copy(stack=False)
        board.push(current_example.move)

        assert board.fen() == next_example.board.fen()


def test_illegal_partial_pgn_is_rejected(game_record):
    malformed_record = dict(game_record)

    malformed_record["movetext"] = "1. e4 e5 2. Nf3 Nc6 3. Bb5 Kd7"

    with pytest.raises(
        ValueError,
        match="PGN contains parsing errors",
    ):
        list(iter_training_examples(malformed_record))


# ------


@pytest.fixture
def game_records(game_record) -> list[dict[str, object]]:
    records = []

    for index in range(10):
        record = dict(game_record)
        record["Site"] = f"https://lichess.org/test-game-{index}"
        records.append(record)

    return records


def test_build_training_examples_expands_all_games(game_records):
    examples = build_training_examples(game_records)

    # Each synthetic game contains 8 plies.
    assert len(examples) == 80


def test_build_training_examples_preserves_game_ids(game_records):
    examples = build_training_examples(game_records)

    source_game_ids = {example.source_game_id for example in examples}

    expected_game_ids = {record["Site"] for record in game_records}

    assert source_game_ids == expected_game_ids


def test_chess_policy_dataset_length(game_record):
    examples = list(iter_training_examples(game_record))

    dataset = ChessPolicyDataset(examples)

    assert len(dataset) == 8


def test_chess_policy_dataset_returns_encoded_sample(game_record):
    examples = list(iter_training_examples(game_record))

    dataset = ChessPolicyDataset(examples)

    x, y = dataset[0]

    assert x.shape == (18, 8, 8)
    assert x.dtype == torch.float32

    assert y.shape == torch.Size([])
    assert y.dtype == torch.long

    assert y.item() == encode_move(examples[0].move)


def test_chess_policy_dataset_first_target_is_e4(game_record):
    examples = list(iter_training_examples(game_record))

    dataset = ChessPolicyDataset(examples)

    _, y = dataset[0]

    expected_move = chess.Move.from_uci("e2e4")

    assert y.item() == encode_move(expected_move)


def test_game_split_sizes(game_records):
    training_records, validation_records = split_game_records(
        game_records,
        validation_fraction=0.2,
        seed=42,
    )

    assert len(training_records) == 8
    assert len(validation_records) == 2


def test_game_split_has_no_game_overlap(game_records):
    training_records, validation_records = split_game_records(
        game_records,
        validation_fraction=0.2,
        seed=42,
    )

    training_ids = {record["Site"] for record in training_records}

    validation_ids = {record["Site"] for record in validation_records}

    assert training_ids.isdisjoint(validation_ids)


def test_game_split_preserves_all_games(game_records):
    training_records, validation_records = split_game_records(
        game_records,
        validation_fraction=0.2,
        seed=42,
    )

    split_ids = {record["Site"] for record in training_records} | {
        record["Site"] for record in validation_records
    }

    original_ids = {record["Site"] for record in game_records}

    assert split_ids == original_ids


def test_game_split_is_deterministic(game_records):
    first_training, first_validation = split_game_records(
        game_records,
        validation_fraction=0.2,
        seed=42,
    )

    second_training, second_validation = split_game_records(
        game_records,
        validation_fraction=0.2,
        seed=42,
    )

    first_training_ids = [record["Site"] for record in first_training]

    second_training_ids = [record["Site"] for record in second_training]

    first_validation_ids = [record["Site"] for record in first_validation]

    second_validation_ids = [record["Site"] for record in second_validation]

    assert first_training_ids == second_training_ids
    assert first_validation_ids == second_validation_ids


def test_training_and_validation_examples_do_not_share_games(
    game_records,
):
    training_records, validation_records = split_game_records(
        game_records,
        validation_fraction=0.2,
        seed=42,
    )

    training_examples = build_training_examples(training_records)

    validation_examples = build_training_examples(validation_records)

    training_game_ids = {example.source_game_id for example in training_examples}

    validation_game_ids = {example.source_game_id for example in validation_examples}

    assert training_game_ids.isdisjoint(validation_game_ids)


def test_all_positions_from_each_game_stay_in_one_split(
    game_records,
):
    training_records, validation_records = split_game_records(
        game_records,
        validation_fraction=0.2,
        seed=42,
    )

    training_examples = build_training_examples(training_records)

    validation_examples = build_training_examples(validation_records)

    training_game_ids = {example.source_game_id for example in training_examples}

    validation_game_ids = {example.source_game_id for example in validation_examples}

    for game_record in game_records:
        game_id = game_record["Site"]

        assert (game_id in training_game_ids) != (game_id in validation_game_ids)


def test_invalid_validation_fraction_is_rejected(game_records):
    for validation_fraction in (
        0.0,
        1.0,
        -0.1,
        1.1,
    ):
        with pytest.raises(
            ValueError,
            match="validation_fraction must be between 0 and 1",
        ):
            split_game_records(
                game_records,
                validation_fraction=validation_fraction,
            )


def test_dataloader_batch_shapes(game_record):
    examples = list(iter_training_examples(game_record))

    dataset = ChessPolicyDataset(examples)

    dataloader = DataLoader(
        dataset,
        batch_size=4,
        shuffle=False,
    )

    x, y = next(iter(dataloader))

    assert x.shape == (4, 18, 8, 8)
    assert x.dtype == torch.float32

    assert y.shape == (4,)
    assert y.dtype == torch.long


def test_dataloader_targets_match_training_examples(game_record):
    examples = list(iter_training_examples(game_record))

    dataset = ChessPolicyDataset(examples)

    dataloader = DataLoader(
        dataset,
        batch_size=4,
        shuffle=False,
    )

    _, y = next(iter(dataloader))

    expected = torch.tensor(
        [encode_move(example.move) for example in examples[:4]],
        dtype=torch.long,
    )

    assert torch.equal(y, expected)
