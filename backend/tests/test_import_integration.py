from backend.services.pgn_import import import_pgn_text
from backend.database.connection import connect
from backend.repositories.games import get_game
from backend.repositories.game_moves import get_moves_for_game


def mark_game_as_test(game_id: str) -> None:
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE games SET source_type = %s WHERE id = %s",
                ("test", game_id),
            )
            conn.commit()
    finally:
        conn.close()


def test_import_pgn_persists_game_and_moves():
    pgn = """[Event "Integration Test"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
"""

    summary = import_pgn_text(pgn, source_filename="integration_test.pgn")
    assert "imported" in summary
    assert len(summary["imported"]) == 1

    game_id = summary["imported"][0]["game_id"]
    mark_game_as_test(game_id)

    game = get_game(game_id)
    assert game is not None
    assert game["source_type"] == "test"
    moves = get_moves_for_game(game_id)
    assert len(moves) == 6
    assert moves[0]["san"] == "e4"
