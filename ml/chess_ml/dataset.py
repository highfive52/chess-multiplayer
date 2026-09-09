"""Training-data construction from Lichess game records."""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any, Iterator, Mapping

import chess
import chess.pgn


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
        raise ValueError(
            f"Unable to parse PGN game: {source_game_id}"
        )

    if game.errors:
        raise ValueError(
            f"PGN contains parsing errors for {source_game_id}: "
            f"{game.errors}"
        )

    board = game.board()

    for ply, move in enumerate(
        game.mainline_moves(),
        start=1,
    ):
        yield TrainingExample(
            board=board.copy(stack=False),
            move=move,
            source_game_id=source_game_id,
            ply=ply,
            white_elo=int(game_record["WhiteElo"]),
            black_elo=int(game_record["BlackElo"]),
        )

        board.push(move)