from typing import Optional, List, Dict
from ..database.connection import connect

try:
    from psycopg import errors
except Exception:
    errors = None


class DuplicateMoveError(Exception):
    pass


def insert_move(
    game_id: str,
    ply: int,
    san: str,
    fen_after: str,
    from_square: Optional[str] = None,
    to_square: Optional[str] = None,
    promotion: Optional[str] = None,
) -> str:
    conn = connect()
    try:
        with conn.cursor() as cur:
            try:
                if ply is None:
                    # Retry loop to handle concurrent inserts that may produce
                    # duplicate (game_id, ply) values due to race windows.
                    import time
                    import random

                    attempts = 5
                    for attempt in range(attempts):
                        try:
                            # Compute next ply atomically within the insert using a CTE
                            cur.execute(
                                """
                                WITH next_ply AS (
                                    SELECT COALESCE(MAX(ply), 0) + 1 AS ply
                                    FROM game_moves
                                    WHERE game_id = %s
                                )
                                INSERT INTO game_moves (game_id, ply, san, fen_after, from_square, to_square, promotion)
                                SELECT %s, next_ply.ply, %s, %s, %s, %s, %s
                                FROM next_ply
                                RETURNING id
                                """,
                                (
                                    game_id,
                                    game_id,
                                    san,
                                    fen_after,
                                    from_square,
                                    to_square,
                                    promotion,
                                ),
                            )
                            break
                        except Exception as e:
                            if errors is not None and isinstance(
                                e, errors.UniqueViolation
                            ):
                                # rollback the failed statement so we can retry
                                try:
                                    conn.rollback()
                                except Exception:
                                    pass
                                # brief randomized backoff and retry
                                if attempt + 1 == attempts:
                                    raise DuplicateMoveError(
                                        "move already exists"
                                    ) from e
                                time.sleep(0.01 + random.random() * 0.02)
                                continue
                            raise
                else:
                    cur.execute(
                        """
                        INSERT INTO game_moves (game_id, ply, san, fen_after, from_square, to_square, promotion)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            game_id,
                            ply,
                            san,
                            fen_after,
                            from_square,
                            to_square,
                            promotion,
                        ),
                    )
            except Exception as e:
                if errors is not None and isinstance(e, errors.UniqueViolation):
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    raise DuplicateMoveError("move already exists") from e
                raise
            move_id = cur.fetchone()[0]
            conn.commit()
            return str(move_id)
    finally:
        conn.close()


def get_moves_for_game(game_id: str) -> List[Dict]:
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ply, san, fen_after, from_square, to_square, promotion, created_at FROM game_moves WHERE game_id = %s ORDER BY ply",
                (game_id,),
            )
            rows = cur.fetchall()
            cols = [d.name for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


def get_move_by_id(move_id: str) -> Optional[Dict]:
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, game_id, ply, san, fen_after, from_square, to_square, promotion, created_at FROM game_moves WHERE id = %s",
                (move_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            cols = [d.name for d in cur.description]
            return dict(zip(cols, row))
    finally:
        conn.close()
