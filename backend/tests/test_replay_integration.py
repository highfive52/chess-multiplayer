import os
import pytest

from backend.database.connection import connect, get_database_url


def _is_db_available():
    url = get_database_url()
    if not url:
        return False
    try:
        conn = connect()
        conn.close()
        return True
    except Exception:
        return False


@pytest.mark.integration
def test_replay_endpoint_integration():
    if not _is_db_available():
        pytest.skip("DATABASE_URL not set or DB not reachable; skip integration tests")

    # apply migrations
    from alembic.config import Config
    from alembic import command

    here = os.path.dirname(os.path.dirname(__file__))
    alembic_ini = os.path.join(here, "alembic.ini")
    alembic_ini = os.path.normpath(alembic_ini)
    cfg = Config(alembic_ini)
    command.upgrade(cfg, "head")

    from backend.repositories import games as games_repo
    from backend.services import game_history
    from backend import main as main_module
    from fastapi.testclient import TestClient

    game_id = games_repo.create_game(None, "startpos", "test")

    try:
        # create a couple of moves
        game_history.record_move(game_id, {"board": None}, "e2", "e4")
        game_history.record_move(game_id, {"board": None}, "e7", "e5")

        client = TestClient(main_module.app)
        resp = client.get(f"/games/{game_id}/replay")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("game_id") == game_id
        assert body.get("initial_fen") is not None
        moves = body.get("moves", [])
        assert len(moves) >= 3
        # ply ordering and presence of ply 0
        plys = [m.get("ply") for m in moves]
        assert plys[0] == 0
        assert plys == sorted(plys)
    finally:
        # cleanup
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM game_moves WHERE game_id = %s", (game_id,))
                cur.execute("DELETE FROM games WHERE id = %s", (game_id,))
                conn.commit()
        finally:
            conn.close()
