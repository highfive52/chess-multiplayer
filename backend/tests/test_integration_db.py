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
def test_db_migrations_and_simple_persistence():
    """Run Alembic migrations (if necessary) and exercise game_history against real DB.

    This test requires `DATABASE_URL` to point at a running Postgres instance
    (e.g. the development docker-compose). If the DB is not available the test
    is skipped.
    """
    if not _is_db_available():
        pytest.skip("DATABASE_URL not set or DB not reachable; skip integration tests")

    # Apply Alembic migrations programmatically using the alembic config in repo
    from alembic.config import Config
    from alembic import command

    here = os.path.dirname(os.path.dirname(__file__))
    alembic_ini = os.path.join(here, "alembic.ini")
    alembic_ini = os.path.normpath(alembic_ini)
    cfg = Config(alembic_ini)
    # alembic/env.py reads DATABASE_URL from env so no further config required
    command.upgrade(cfg, "head")

    # Now run a simple persistence flow
    from backend.repositories import games as games_repo
    from backend.services import game_history

    game_id = games_repo.create_game(None, "startpos", "live")
    assert game_id

    try:
        # record a simple move
        out = game_history.record_move(game_id, {"board": None}, "e2", "e4")
        assert out.get("san") == "e4"

        # verify persistent rows exist
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, initial_fen FROM games WHERE id = %s", (game_id,)
                )
                row = cur.fetchone()
                assert row is not None

                cur.execute(
                    "SELECT count(*) FROM game_moves WHERE game_id = %s", (game_id,)
                )
                cnt = cur.fetchone()[0]
                assert cnt >= 1
        finally:
            conn.close()
    finally:
        # teardown: remove created moves and game so test is idempotent
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM game_moves WHERE game_id = %s", (game_id,))
                cur.execute("DELETE FROM games WHERE id = %s", (game_id,))
                conn.commit()
        finally:
            conn.close()


@pytest.mark.integration
def test_concurrent_move_inserts():
    """Create a game and insert many moves concurrently using the repository.

    Verifies that the repository's atomic ply calculation prevents collisions
    and results in consecutive ply values.
    """
    if not _is_db_available():
        pytest.skip("DATABASE_URL not set or DB not reachable; skip integration tests")

    # ensure migrations applied
    from alembic.config import Config
    from alembic import command

    here = os.path.dirname(os.path.dirname(__file__))
    alembic_ini = os.path.join(here, "alembic.ini")
    alembic_ini = os.path.normpath(alembic_ini)
    cfg = Config(alembic_ini)
    command.upgrade(cfg, "head")

    from backend.repositories import games as games_repo
    from backend.repositories import game_moves as moves_repo

    game_id = games_repo.create_game(None, "startpos", "live")

    insert_count = 10

    import threading

    def worker(i):
        # simple distinct SAN/fen per thread
        san = f"m{i}"
        fen = f"fen{i}"
        moves_repo.insert_move(game_id, None, san, fen)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(insert_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Validate results
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ply, san FROM game_moves WHERE game_id = %s ORDER BY ply",
                (game_id,),
            )
            rows = cur.fetchall()
            assert len(rows) == insert_count
            plys = [r[0] for r in rows]
            assert plys == list(range(1, insert_count + 1))
    finally:
        # teardown
        conn2 = connect()
        try:
            with conn2.cursor() as cur:
                cur.execute("DELETE FROM game_moves WHERE game_id = %s", (game_id,))
                cur.execute("DELETE FROM games WHERE id = %s", (game_id,))
                conn2.commit()
        finally:
            conn2.close()
