from fastapi.testclient import TestClient

from backend.services import replay as replay_service
import backend.main as main


def test_get_replay_service_and_route(monkeypatch):
    # Arrange: stub game and moves
    fake_game = {
        "id": "4d5cc218-6ac8-4d9e-893c-628efdbd214a",
        "room_code": "ABCD",
        "source_type": "live",
        "initial_fen": "startpos",
        "final_fen": None,
        "status": "active",
        "result": None,
        "started_at": None,
        "completed_at": None,
        "created_at": "2026-09-02T00:00:00Z",
        "updated_at": "2026-09-02T00:00:00Z",
    }

    fake_moves = [
        {
            "ply": 1,
            "san": "e4",
            "fen_after": "fen1",
            "from_square": "e2",
            "to_square": "e4",
            "created_at": "2026-09-02T00:00:00Z",
        },
        {
            "ply": 2,
            "san": "e5",
            "fen_after": "fen2",
            "from_square": "e7",
            "to_square": "e5",
            "created_at": "2026-09-02T00:00:01Z",
        },
    ]

    monkeypatch.setattr(replay_service.games_repo, "get_game", lambda gid: fake_game)
    monkeypatch.setattr(
        replay_service.moves_repo, "get_moves_for_game", lambda gid: fake_moves
    )

    gid = fake_game["id"]

    # Service-level assertion
    doc = replay_service.get_replay_document(gid)
    assert doc["game_id"] == fake_game["id"]
    assert len(doc["moves"]) == 3
    assert doc["moves"][0]["ply"] == 0
    assert doc["moves"][0]["fen_after"] == fake_game["initial_fen"]

    # Route-level assertion using TestClient
    client = TestClient(main.app)
    resp = client.get(f"/games/{gid}/replay")
    assert resp.status_code == 200
    body = resp.json()
    assert body["game_id"] == gid
    assert len(body["moves"]) == 3
    assert body["moves"][0]["ply"] == 0


def test_get_replay_route_404(monkeypatch):
    monkeypatch.setattr(replay_service.games_repo, "get_game", lambda gid: None)
    client = TestClient(main.app)
    resp = client.get("/games/unknown/replay")
    assert resp.status_code == 404
