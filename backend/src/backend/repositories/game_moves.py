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
                    # Lock the owning game row so concurrent inserts for the
                    # same game serialize before computing the next ply.
                    cur.execute(
                        "SELECT 1 FROM games WHERE id = %s FOR UPDATE",
                        (game_id,),
                    )

                    # Compute next ply while holding the game lock to avoid
                    # duplicate (game_id, ply) values under concurrency.
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
