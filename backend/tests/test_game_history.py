from backend.services import game_history


def test_record_move_creates_and_returns_move(monkeypatch):
    # Arrange: stub game exists
    monkeypatch.setattr(game_history.games_repo, "get_game", lambda gid: {"id": gid})

    # No existing moves
    monkeypatch.setattr(game_history.moves_repo, "get_moves_for_game", lambda gid: [])

    # Insert returns a fake UUID
    monkeypatch.setattr(
        game_history.moves_repo, "insert_move", lambda *args, **kwargs: "mock-move-id"
    )
    # get_move_by_id should return the inserted move metadata
    monkeypatch.setattr(
        game_history.moves_repo,
        "get_move_by_id",
        lambda mid: {"id": mid, "ply": 1, "san": "e4", "fen_after": "dummyfen"},
    )

    # Act
    out = game_history.record_move("game-1", None, "e2", "e4")

    # Assert
    assert out["id"] == "mock-move-id"
    assert out["ply"] == 1
    assert out["san"] == "e4"


def test_record_move_idempotent_on_duplicate(monkeypatch):
    # Arrange: game exists
    monkeypatch.setattr(game_history.games_repo, "get_game", lambda gid: {"id": gid})

    # Existing move present for ply 1
    existing = {"id": "existing-id", "ply": 1, "san": "e4", "fen_after": "dummyfen"}
    monkeypatch.setattr(
        game_history.moves_repo, "get_moves_for_game", lambda gid: [existing]
    )

    # Insert raises DuplicateMoveError
    def _insert(*args, **kwargs):
        raise game_history.DuplicateMoveError()

    monkeypatch.setattr(game_history.moves_repo, "insert_move", _insert)

    # Act
    out = game_history.record_move("game-1", None, "e2", "e4")

    # Assert: returned existing move
    assert out["id"] == "existing-id"
    assert out["ply"] == 1
    assert out["san"] == "e4"
