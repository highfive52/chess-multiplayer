from pathlib import Path
import os

from fastapi.testclient import TestClient

from backend.database.connection import connect
from backend.main import app
from backend.repositories.games import get_game


FIXTURES = Path(__file__).parent / "fixtures" / "pgn"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


def ensure_database_env() -> None:
    if "DATABASE_URL" not in os.environ:
        here = os.path.join(os.path.dirname(__file__), "..", "..")
        env_path = os.path.join(here, ".env.example")
        try:
            with open(env_path, "r") as f:
                for line in f:
                    if line.startswith("DATABASE_URL="):
                        os.environ["DATABASE_URL"] = line.strip().split("=", 1)[1]
                        break
        except Exception:
            pass


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


def test_import_pgn_multi_game_text_returns_two_rows():
    ensure_database_env()
    client = TestClient(app)

    resp = client.post(
        "/games/import/pgn", json={"text": load_fixture("multiple_games.pgn")}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["imported"]) == 2

    game_ids = [row["game_id"] for row in body["imported"]]
    try:
        for game_id in game_ids:
            mark_game_as_test(game_id)
            assert get_game(game_id) is not None
    finally:
        for game_id in game_ids:
            cleanup_game(game_id)


def test_import_pgn_comments_nags_and_variations_show_warnings():
    ensure_database_env()
    client = TestClient(app)

    resp = client.post(
        "/games/import/pgn", json={"text": load_fixture("comments_and_nags.pgn")}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["imported"]) == 1
    warnings = set(body["imported"][0]["warnings"])
    assert {"COMMENTS_IGNORED", "NAGS_IGNORED"}.issubset(warnings)

    game_id = body["imported"][0]["game_id"]
    try:
        mark_game_as_test(game_id)
        assert get_game(game_id) is not None
    finally:
        cleanup_game(game_id)

    resp = client.post(
        "/games/import/pgn", json={"text": load_fixture("variations.pgn")}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["imported"]) == 1
    assert "VARIATIONS_IGNORED" in body["imported"][0]["warnings"]

    game_id = body["imported"][0]["game_id"]
    try:
        mark_game_as_test(game_id)
        assert get_game(game_id) is not None
    finally:
        cleanup_game(game_id)


def test_import_pgn_custom_fen_persists_initial_position():
    ensure_database_env()
    client = TestClient(app)

    resp = client.post(
        "/games/import/pgn", json={"text": load_fixture("promotion.pgn")}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["imported"]) == 1

    game_id = body["imported"][0]["game_id"]
    try:
        mark_game_as_test(game_id)
        game = get_game(game_id)
        assert game is not None
        assert game["initial_fen"] == "6k1/4P3/8/8/8/8/8/4K3 w - - 0 1"
    finally:
        cleanup_game(game_id)


def test_import_pgn_rejects_empty_input():
    ensure_database_env()
    client = TestClient(app)

    resp = client.post("/games/import/pgn", json={})
    assert resp.status_code == 400


def test_import_pgn_rejects_malformed_input():
    ensure_database_env()
    client = TestClient(app)

    resp = client.post(
        "/games/import/pgn", json={"text": load_fixture("malformed.pgn")}
    )
    assert resp.status_code == 500
