import os
from fastapi.testclient import TestClient

from backend.main import app
from backend.database.connection import connect
from backend.repositories.games import get_game


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


def ensure_database_env():
    # If DATABASE_URL not set, try to read from repo .env.example
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


def test_import_pgn_via_text_endpoint():
    ensure_database_env()
    client = TestClient(app)
    pgn = """[Event "API Test"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
"""

    resp = client.post("/games/import/pgn", json={"text": pgn})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "imported" in body
    assert len(body["imported"]) == 1
    gid = body["imported"][0]["game_id"]
    mark_game_as_test(gid)
    game = get_game(gid)
    assert game is not None


def test_import_pgn_via_file_endpoint():
    ensure_database_env()
    client = TestClient(app)
    pgn = """[Event "API Test File"]
[White "Carol"]
[Black "Dan"]
[Result "0-1"]

1. d4 d5 2. c4 c6 0-1
"""

    files = {"file": ("sample.pgn", pgn, "text/plain")}
    resp = client.post("/games/import/pgn", files=files)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "imported" in body
    assert len(body["imported"]) == 1
    gid = body["imported"][0]["game_id"]
    mark_game_as_test(gid)
    game = get_game(gid)
    assert game is not None


def test_import_and_replay_roundtrip():
    ensure_database_env()
    client = TestClient(app)
    pgn = """[Event "Replay Test"]
[White "Eve"]
[Black "Frank"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 1-0
"""

    resp = client.post("/games/import/pgn", json={"text": pgn})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "imported" in body and len(body["imported"]) == 1
    gid = body["imported"][0]["game_id"]
    mark_game_as_test(gid)

    # Fetch replay document
    r = client.get(f"/games/{gid}/replay")
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["game_id"] == gid
    # There should be at least ply 0 + 4 moves
    assert isinstance(doc.get("moves"), list)
    assert len(doc["moves"]) >= 5
