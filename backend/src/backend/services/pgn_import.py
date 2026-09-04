"""PGN import service (Phase 3): parsing and normalization using python-chess.

Provides `parse_pgn(text)` which returns a list of `ParsedPgnGame` objects
by parsing one or more games from the provided PGN text. Parsing uses
`python-chess` and normalizes each mainline move into the application's
`ImportedMove` shape.
"""

from typing import List, TextIO
import io

import chess
import chess.pgn

from backend.schemas.pgn_import import ParsedPgnGame, ImportedMove
from ..database.connection import connect
from datetime import datetime, timezone

try:
    import psycopg
    from psycopg import errors as pg_errors
except Exception:  # pragma: no cover - psycopg may be installed in test env
    psycopg = None
    pg_errors = None


def normalize_game(game: chess.pgn.Game) -> ParsedPgnGame:
    """Normalize a `chess.pgn.Game` into `ParsedPgnGame`.

    Captures headers, starting FEN (when present), and the mainline moves.
    Raises a ValueError on unexpected parsing issues.
    """
    headers = dict(game.headers)

    # Determine initial FEN: use FEN header only when SetUp == "1"
    initial_fen = None
    if headers.get("SetUp") == "1" and headers.get("FEN"):
        initial_fen = headers.get("FEN")

    board = chess.Board(fen=initial_fen) if initial_fen else chess.Board()

    # Detect warnings: comments, NAGs, variations, unknown tags
    warnings: List[str] = []
    has_comment = False
    has_nag = False
    has_variation = False

    # Known tags we care about; others are "unknown"
    known_tags = {
        "Event",
        "Site",
        "Date",
        "Round",
        "White",
        "Black",
        "Result",
        "FEN",
        "SetUp",
    }
    unknown_tags = [k for k in headers.keys() if k not in known_tags]
    if unknown_tags:
        warnings.append("UNKNOWN_TAGS_IGNORED")

    # Walk the full game tree to detect comments, nags, and variations
    stack = [game]
    while stack:
        node = stack.pop()
        try:
            if getattr(node, "comment", None):
                has_comment = True
            nags = getattr(node, "nags", None)
            if nags:
                # python-chess represents NAGs as a set of ints
                if len(nags) > 0:
                    has_nag = True
            vars_ = getattr(node, "variations", None)
            if vars_:
                # If any node has more than one variation branch, record it
                if len(vars_) > 1:
                    has_variation = True
                for child in vars_:
                    stack.append(child)
        except Exception:
            # Be forgiving for unexpected node shapes
            continue

    if has_comment:
        warnings.append("COMMENTS_IGNORED")
    if has_nag:
        warnings.append("NAGS_IGNORED")
    if has_variation:
        warnings.append("VARIATIONS_IGNORED")

    moves: List[ImportedMove] = []
    ply = 1

    try:
        for node in game.mainline():
            move = node.move
            if move is None:
                continue

            # SAN must be generated against the board before pushing the move
            san = board.san(move)

            from_sq = (
                chess.square_name(move.from_square)
                if move.from_square is not None
                else None
            )
            to_sq = (
                chess.square_name(move.to_square)
                if move.to_square is not None
                else None
            )

            promotion = None
            if move.promotion:
                # chess.piece_symbol returns a lowercase single-letter
                promotion = chess.piece_symbol(move.promotion).lower()

            board.push(move)
            fen_after = board.fen()

            moves.append(
                ImportedMove(
                    ply=ply,
                    san=san,
                    fen_after=fen_after,
                    from_square=from_sq,
                    to_square=to_sq,
                    promotion=promotion,
                )
            )
            ply += 1
    except Exception as exc:  # pragma: no cover - surface parse issues
        raise ValueError(f"Error normalizing game: {exc}") from exc

    return ParsedPgnGame(
        metadata=headers, initial_fen=initial_fen, moves=moves, warnings=warnings
    )


def parse_pgn(text: str) -> List[ParsedPgnGame]:
    """Parse PGN text and return a list of `ParsedPgnGame`.

    Reads multiple games from the provided text until EOF. Each game is
    normalized and returned. Parsing errors raise `ValueError` with context.
    """
    pgn: TextIO = io.StringIO(text)
    parsed_games: List[ParsedPgnGame] = []
    game_index = 0
    # File-level heuristics: if the raw PGN contains parentheses, it likely
    # includes inline variations. python-chess may ignore malformed
    # variations during parsing, so surface a warning to the caller.
    has_parentheses = ("(" in text) or (")" in text)

    while True:
        game = chess.pgn.read_game(pgn)
        if game is None:
            break
        game_index += 1
        try:
            parsed = normalize_game(game)
            # Propagate file-level variation warning when parentheses were present
            if has_parentheses and "VARIATIONS_IGNORED" not in parsed.warnings:
                parsed.warnings.append("VARIATIONS_IGNORED")
            parsed_games.append(parsed)
        except Exception as exc:  # pragma: no cover - bubbled to caller
            raise ValueError(
                f"Failed to parse game at index {game_index}: {exc}"
            ) from exc

    return parsed_games


def persist_parsed_game(
    parsed: ParsedPgnGame, source_filename: str | None = None
) -> str:
    """Persist a single ParsedPgnGame transactionally and return `game_id`.

    Each game is persisted in its own DB transaction. On failure the
    transaction is rolled back and an exception is raised.
    """
    conn = connect()
    try:
        with conn.cursor() as cur:
            try:
                # Start a transaction for this game
                # Ensure initial_fen is non-null (DB requires it)
                initial_fen = parsed.initial_fen or chess.Board().fen()
                final_fen = parsed.moves[-1].fen_after if parsed.moves else initial_fen
                result = (
                    parsed.metadata.get("Result")
                    if isinstance(parsed.metadata, dict)
                    else None
                )

                cur.execute(
                    """
                    INSERT INTO games (room_code, source_type, initial_fen, final_fen, status, result, source_filename, imported_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        None,
                        "pgn_import",
                        initial_fen,
                        final_fen,
                        "completed",
                        result,
                        source_filename,
                        datetime.now(timezone.utc),
                    ),
                )
                game_id = str(cur.fetchone()[0])

                # Insert moves sequentially; if any insert fails, rollback the whole game
                for m in parsed.moves:
                    try:
                        cur.execute(
                            """
                            INSERT INTO game_moves (game_id, ply, san, fen_after, from_square, to_square, promotion)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            RETURNING id
                            """,
                            (
                                game_id,
                                m.ply,
                                m.san,
                                m.fen_after,
                                m.from_square,
                                m.to_square,
                                m.promotion,
                            ),
                        )
                    except Exception as e:
                        # Map well-known DB errors to structured diagnostics
                        code = "IMPORT_ERROR"
                        if pg_errors is not None and isinstance(
                            e, pg_errors.UniqueViolation
                        ):
                            code = "DUPLICATE_MOVE"
                        elif isinstance(e, ValueError):
                            code = "INVALID_MOVE"
                        # Rollback the whole game transaction
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        raise RuntimeError(
                            {
                                "code": code,
                                "message": str(e),
                                "ply": m.ply,
                            }
                        ) from e

                conn.commit()
                return game_id
            except Exception:
                # Ensure rollback if anything unexpected happened
                try:
                    conn.rollback()
                except Exception:
                    pass
                raise
    finally:
        conn.close()


def import_pgn_text(text: str, source_filename: str | None = None) -> dict:
    """Parse and persist PGN text. Returns a summary dict with `imported` and `failed` lists."""
    parsed_games = parse_pgn(text)
    imported = []
    failed = []
    for idx, pg in enumerate(parsed_games, start=1):
        try:
            gid = persist_parsed_game(pg, source_filename=source_filename)
            imported.append(
                {
                    "game_index": idx,
                    "game_id": gid,
                    "move_count": len(pg.moves),
                    "warnings": getattr(pg, "warnings", []),
                }
            )
        except RuntimeError as re:
            # RuntimeError from persist_parsed_game carries a dict payload
            payload = re.args[0] if re.args else {}
            if isinstance(payload, dict):
                failed.append(
                    {
                        "game_index": idx,
                        "code": payload.get("code", "IMPORT_ERROR"),
                        "ply": payload.get("ply"),
                        "message": payload.get("message"),
                    }
                )
            else:
                failed.append(
                    {"game_index": idx, "code": "IMPORT_ERROR", "message": str(re)}
                )
        except Exception as exc:
            # Generic fallback
            failed.append(
                {"game_index": idx, "code": "IMPORT_ERROR", "message": str(exc)}
            )
    return {"imported": imported, "failed": failed}
