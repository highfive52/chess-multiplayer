from typing import Optional, Dict
from ..database.connection import connect


def create_game(
    room_code: Optional[str], initial_fen: str, source_type: str = "live"
) -> str:
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO games (room_code, initial_fen, source_type)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (room_code, initial_fen, source_type),
            )
            game_id = cur.fetchone()[0]
            conn.commit()
            return str(game_id)
    finally:
        conn.close()


def get_game(game_id: str) -> Optional[Dict]:
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM games WHERE id = %s", (game_id,))
            row = cur.fetchone()
            if not row:
                return None
            cols = [d.name for d in cur.description]
            return dict(zip(cols, row))
    finally:
        conn.close()


def complete_game(
    game_id: str,
    result: Optional[str],
    final_fen: Optional[str],
    status: str = "completed",
) -> None:
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE games
                SET status = %s,
                    result = %s,
                    final_fen = %s,
                    completed_at = now(),
                    updated_at = now()
                WHERE id = %s
                """,
                (status, result, final_fen, game_id),
            )
            conn.commit()
    finally:
        conn.close()


def list_games(source_type: Optional[str] = None, limit: int = 50):
    conn = connect()
    try:
        with conn.cursor() as cur:
            if source_type:
                cur.execute(
                    "SELECT id, room_code, source_type, created_at FROM games WHERE source_type = %s ORDER BY created_at DESC LIMIT %s",
                    (source_type, limit),
                )
            else:
                cur.execute(
                    "SELECT id, room_code, source_type, created_at FROM games ORDER BY created_at DESC LIMIT %s",
                    (limit,),
                )
            rows = cur.fetchall()
            cols = [d.name for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()
