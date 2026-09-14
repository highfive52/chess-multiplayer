"""Training-data construction from Lichess game records."""

from __future__ import annotations

import io
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import chess
import chess.pgn
import torch
from encoding import encode_board
from moves import encode_move
from torch.utils.data import Dataset, random_split


@dataclass(frozen=True)
class TrainingExample:
    """One supervised chess-policy training observation."""

    board: chess.Board
    move: chess.Move
    source_game_id: str
    ply: int
    white_elo: int
    black_elo: int


def iter_training_examples(
    game_record: Mapping[str, Any],
) -> Iterator[TrainingExample]:
    """Yield supervised observations from one Lichess game."""

    movetext = game_record["movetext"]

    pgn_text = f"""
[Event "?"]
[Site "{game_record.get("Site", "?")}"]
[Date "????.??.??"]
[Round "?"]
[White "?"]
[Black "?"]
[Result "{game_record.get("Result", "*")}"]

{movetext}
"""

    game = chess.pgn.read_game(io.StringIO(pgn_text))

    source_game_id = str(game_record.get("Site", ""))

    if game is None:
        raise ValueError(f"Unable to parse PGN game: {source_game_id}")

    if game.errors:
        raise ValueError(
            f"PGN contains parsing errors for {source_game_id}: {game.errors}"
        )

    board = game.board()

    for ply, move in enumerate(game.mainline_moves(), start=1):
        yield TrainingExample(
            board=board.copy(stack=False),
            move=move,
            source_game_id=source_game_id,
            ply=ply,
            white_elo=int(game_record["WhiteElo"]),
            black_elo=int(game_record["BlackElo"]),
        )

        board.push(move)


class ChessPolicyDataset(Dataset):
    """PyTorch dataset of encoded chess-policy observations."""

    def __init__(
        self,
        examples: Sequence[TrainingExample],
    ) -> None:
        self.examples = list(examples)

    def __len__(self) -> int:
        """Return the number of training observations."""

        return len(self.examples)

    def __getitem__(
        self,
        index: int,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Return one encoded board and move target."""

        example = self.examples[index]

        x = encode_board(example.board)

        y = torch.tensor(
            encode_move(example.move),
            dtype=torch.long,
        )

        return x, y


def build_training_examples(
    game_records: Sequence[Mapping[str, Any]],
) -> list[TrainingExample]:
    """Expand game records into supervised training observations."""

    examples: list[TrainingExample] = []

    for game_record in game_records:
        examples.extend(iter_training_examples(game_record))

    return examples


def split_game_records(
    game_records: Sequence[Mapping[str, Any]],
    *,
    validation_fraction: float = 0.2,
    seed: int = 42,
) -> tuple[Sequence[Mapping[str, Any]], Sequence[Mapping[str, Any]]]:
    """Split game records into training and validation sets."""

    if not 0.0 < validation_fraction < 1.0:
        raise ValueError("validation_fraction must be between 0 and 1")

    generator = torch.Generator().manual_seed(seed)

    training_records, validation_records = random_split(
        game_records,
        [1.0 - validation_fraction, validation_fraction],
        generator=generator,
    )

    return training_records, validation_records
