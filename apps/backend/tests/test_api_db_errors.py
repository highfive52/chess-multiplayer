import main as backend_main
from fastapi.testclient import TestClient
from main import app
from psycopg import OperationalError


def test_list_games_returns_service_unavailable_on_db_error(monkeypatch):
    def raise_db_error(*args, **kwargs):
        raise OperationalError("db down")

    monkeypatch.setattr(backend_main.games_repo, "list_games", raise_db_error)

    client = TestClient(app)
    resp = client.get("/games")

    assert resp.status_code == 503
    assert resp.json()["detail"] == "unable to list games: db down"


def test_import_pgn_returns_service_unavailable_on_db_error(monkeypatch):
    def raise_db_error(*args, **kwargs):
        raise OperationalError("db down")

    monkeypatch.setattr(backend_main, "import_pgn_text", raise_db_error)

    client = TestClient(app)
    resp = client.post(
        "/games/import/pgn", json={"text": '[Event "Test"]\n\n1. e4 e5 1-0\n'}
    )

    assert resp.status_code == 503
    assert resp.json()["detail"] == "import failed: db down"
