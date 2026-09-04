from pathlib import Path

import chess
import pytest

from backend.services.pgn_import import parse_pgn


FIXTURES = Path(__file__).parent / "fixtures" / "pgn"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


def expected_fens(start_fen: str | None, sans: list[str]) -> list[str]:
    board = chess.Board(start_fen) if start_fen else chess.Board()
    fens = []
    for san in sans:
        board.push_san(san)
        fens.append(board.fen())
    return fens


def test_parse_standard_game_fixture() -> None:
    games = parse_pgn(load_fixture("simple_game.pgn"))

    assert len(games) == 1
    game = games[0]
    assert game.metadata["White"] == "Alice"
    assert [move.san for move in game.moves] == ["e4", "e5", "Nf3", "Nc6"]
    assert [move.from_square for move in game.moves] == ["e2", "e7", "g1", "b8"]
    assert [move.to_square for move in game.moves] == ["e4", "e5", "f3", "c6"]
    assert [move.fen_after for move in game.moves] == expected_fens(
        None, ["e4", "e5", "Nf3", "Nc6"]
    )


def test_parse_castling_fixture() -> None:
    games = parse_pgn(load_fixture("castling.pgn"))

    assert len(games) == 1
    game = games[0]
    assert [move.san for move in game.moves] == ["O-O", "O-O-O"]
    assert [move.from_square for move in game.moves] == ["e1", "e8"]
    assert [move.to_square for move in game.moves] == ["g1", "c8"]
    assert [move.fen_after for move in game.moves] == expected_fens(
        "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", ["O-O", "O-O-O"]
    )


def test_parse_capture_fixture() -> None:
    games = parse_pgn(load_fixture("capture.pgn"))

    game = games[0]
    assert game.moves[-1].san == "Bxc6"
    assert game.moves[-1].from_square == "b5"
    assert game.moves[-1].to_square == "c6"


def test_parse_check_and_mate_fixtures() -> None:
    check_game = parse_pgn(load_fixture("check.pgn"))[0]
    assert check_game.moves[0].san == "Qh5+"

    mate_game = parse_pgn(load_fixture("checkmate.pgn"))[0]
    assert mate_game.moves[-1].san == "Qxf7#"
    assert mate_game.moves[-1].san.endswith("#")


def test_parse_promotion_fixture() -> None:
    game = parse_pgn(load_fixture("promotion.pgn"))[0]

    assert game.initial_fen == "6k1/4P3/8/8/8/8/8/4K3 w - - 0 1"
    assert game.moves[0].san == "e8=Q+"
    assert game.moves[0].promotion == "q"
    assert game.moves[0].from_square == "e7"
    assert game.moves[0].to_square == "e8"


def test_parse_disambiguation_fixture() -> None:
    game = parse_pgn(load_fixture("custom_fen.pgn"))[0]

    assert game.initial_fen == "8/8/8/8/8/8/1N3N2/4K2k w - - 0 1"
    assert game.moves[0].san == "Nbd3+"
    assert game.moves[0].from_square == "b2"
    assert game.moves[0].to_square == "d3"


def test_parse_comments_nags_and_variations() -> None:
    comments = parse_pgn(load_fixture("comments_and_nags.pgn"))[0]
    assert {"COMMENTS_IGNORED", "NAGS_IGNORED"}.issubset(set(comments.warnings))
    assert [move.san for move in comments.moves] == [
        "e4",
        "e5",
        "Nf3",
        "Nc6",
        "Bb5",
        "a6",
    ]

    variations = parse_pgn(load_fixture("variations.pgn"))[0]
    assert "VARIATIONS_IGNORED" in variations.warnings
    assert [move.san for move in variations.moves][:2] == ["e4", "e5"]


def test_parse_multiple_games_fixture() -> None:
    games = parse_pgn(load_fixture("multiple_games.pgn"))

    assert len(games) == 2
    assert games[0].metadata["Event"] == "Game 1"
    assert games[1].metadata["Event"] == "Game 2"


def test_parse_malformed_fixture_raises_value_error() -> None:
    with pytest.raises(ValueError):
        parse_pgn(load_fixture("malformed.pgn"))
