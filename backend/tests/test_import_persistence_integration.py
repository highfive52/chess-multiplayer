from pathlib import Path

import pytest

from backend.database.connection import connect, get_database_url
from backend.repositories.game_moves import get_moves_for_game
from backend.repositories.games import get_game
from backend.schemas.pgn_import import ImportedMove, ParsedPgnGame
from backend.services.pgn_import import import_pgn_text, persist_parsed_game


FIXTURES = Path(__file__).parent / "fixtures" / "pgn"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


def _is_db_available() -> bool:
    if not get_database_url():
        return False
    try:
        conn = connect()
        conn.close()
        return True
    except Exception:
        return False


def mark_game_as_test(game_id: str) -> None:
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE games SET source_type = %s WHERE id = %s", ("test", game_id)
            )
            conn.commit()
    finally:
        conn.close()


def cleanup_game(game_id: str) -> None:
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM game_moves WHERE game_id = %s", (game_id,))
            cur.execute("DELETE FROM games WHERE id = %s", (game_id,))
            conn.commit()
    finally:
        conn.close()


@pytest.mark.integration
def test_import_pgn_persists_standard_game_data():
    if not _is_db_available():
        pytest.skip("DATABASE_URL not set or DB not reachable; skip integration tests")

    summary = import_pgn_text(
        load_fixture("simple_game.pgn"), source_filename="simple_game.pgn"
    )
    assert len(summary["imported"]) == 1
    game_id = summary["imported"][0]["game_id"]
    mark_game_as_test(game_id)

    try:
        game = get_game(game_id)
        assert game is not None
        assert game["source_type"] == "test"
        assert game["source_filename"] == "simple_game.pgn"
        assert game["imported_at"] is not None
        assert (
            game["initial_fen"]
            == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        )
        assert (
            game["final_fen"]
            == "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"
        )
        assert game["result"] == "1-0"

        moves = get_moves_for_game(game_id)
        assert [move["ply"] for move in moves] == [1, 2, 3, 4]
        assert [move["san"] for move in moves] == ["e4", "e5", "Nf3", "Nc6"]
        assert [move["from_square"] for move in moves] == ["e2", "e7", "g1", "b8"]
        assert [move["to_square"] for move in moves] == ["e4", "e5", "f3", "c6"]
        assert (
            moves[0]["fen_after"]
            == "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        )
        assert moves[-1]["fen_after"] == game["final_fen"]

    finally:
        cleanup_game(game_id)


@pytest.mark.integration
def test_import_pgn_persists_promotion_and_custom_fen():
    if not _is_db_available():
        pytest.skip("DATABASE_URL not set or DB not reachable; skip integration tests")

    summary = import_pgn_text(
        load_fixture("promotion.pgn"), source_filename="promotion.pgn"
    )
    assert len(summary["imported"]) == 1
    game_id = summary["imported"][0]["game_id"]
    mark_game_as_test(game_id)

    try:
        game = get_game(game_id)
        assert game is not None
        assert game["initial_fen"] == "6k1/4P3/8/8/8/8/8/4K3 w - - 0 1"
        assert game["final_fen"] == "4Q1k1/8/8/8/8/8/8/4K3 b - - 0 1"
        assert game["source_type"] == "test"

        moves = get_moves_for_game(game_id)
        assert len(moves) == 1
        assert moves[0]["san"] == "e8=Q+"
        assert moves[0]["promotion"] == "q"
        assert moves[0]["from_square"] == "e7"
        assert moves[0]["to_square"] == "e8"

    finally:
        cleanup_game(game_id)


@pytest.mark.integration
def test_persist_parsed_game_rolls_back_on_duplicate_ply():
    if not _is_db_available():
        pytest.skip("DATABASE_URL not set or DB not reachable; skip integration tests")

    parsed = ParsedPgnGame(
        metadata={"Event": "Rollback"},
        initial_fen="startpos",
        moves=[
            ImportedMove(
                ply=1,
                san="e4",
                fen_after="fen-after-1",
                from_square="e2",
                to_square="e4",
            ),
            ImportedMove(
                ply=1,
                san="e5",
                fen_after="fen-after-2",
                from_square="e7",
                to_square="e5",
            ),
        ],
    )

    source_filename = "rollback-test.pgn"

    with pytest.raises(RuntimeError):
        persist_parsed_game(parsed, source_filename=source_filename)

    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM games WHERE source_filename = %s",
                (source_filename,),
            )
            assert cur.fetchone()[0] == 0
            cur.execute(
                """
                SELECT count(*)
                FROM game_moves gm
                JOIN games g ON g.id = gm.game_id
                WHERE g.source_filename = %s
                """,
                (source_filename,),
            )
            assert cur.fetchone()[0] == 0
    finally:
        conn.close()
