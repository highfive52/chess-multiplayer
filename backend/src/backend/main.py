import asyncio
import json
import os
import random
import string
import traceback
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
import socketio
from fastapi import Body, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.repositories import games as games_repo
from backend.schemas.pgn_import import ImportResponse
from backend.schemas.replay import ReplayDocument
from backend.services import replay as replay_service
from backend.services.bot_move import generate_bot_move
from backend.services.game_history import create_game_record, record_move
from backend.services.game_move import (
    execute_move,
    final_fen,
)
from backend.services.ml_player import MLPlayer
from backend.services.pgn_import import import_pgn_text

# 1. Configure the Redis connection string (Defaulting to Docker localhost)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis = aioredis.from_url(
    REDIS_URL,
    decode_responses=True,
)


# 2. Setup Socket.io and FastAPI boundaries
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize long-lived application services."""

    print("[ML] Loading chess policy model...")

    app.state.ml_player = MLPlayer()

    print("[ML] Chess policy model loaded.")

    yield


app = FastAPI(
    lifespan=lifespan,
)

socket_app = socketio.ASGIApp(
    sio,
)

app.mount(
    "/socket.io",
    socket_app,
)

asgi_app = app

# Build list of allowed origins
origins = [
    "https://highfive52.github.io",  # Production GitHub Pages
    "http://localhost:5173",  # Vite dev server default
    "http://localhost:5175",  # Alternate Vite dev server
]

# Allow overriding/adding extra origins dynamically via environment variables
if custom_origins := os.environ.get("ALLOWED_ORIGINS"):
    origins.extend(
        [origin.strip() for origin in custom_origins.split(",") if origin.strip()]
    )

# Apply CORS middleware to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

IMPORT_PGN_FILE = File(None)
IMPORT_PGN_TEXT = Body(None)


def create_initial_board():
    return [
        # 👑 Row 0: Black Major Pieces
        [
            {"type": "r", "color": "b"},  # 0 (a8)
            {"type": "n", "color": "b"},  # 1 (b8)
            {"type": "b", "color": "b"},  # 2 (c8)
            {"type": "q", "color": "b"},  # 3 (d8) ◄ Queen on her own color
            {"type": "k", "color": "b"},  # 4 (e8) ◄ King on e-file
            {"type": "b", "color": "b"},  # 5 (f8)
            {"type": "n", "color": "b"},  # 6 (g8)
            {"type": "r", "color": "b"},  # 7 (h8)
        ],
        # ♟️ Row 1: Black Pawns
        [{"type": "p", "color": "b"} for _ in range(8)],
        # 🟩 Rows 2-5: Empty Midground Squares
        [None] * 8,
        [None] * 8,
        [None] * 8,
        [None] * 8,
        # ♟️ Row 6: White Pawns
        [{"type": "p", "color": "w"} for _ in range(8)],
        # 👑 Row 7: White Major Pieces
        [
            {"type": "r", "color": "w"},  # 0 (a1)
            {"type": "n", "color": "w"},  # 1 (b1)
            {"type": "b", "color": "w"},  # 2 (c1)
            {"type": "q", "color": "w"},  # 3 (d1) ◄ Queen on her own color
            {"type": "k", "color": "w"},  # 4 (e1) ◄ King on e-file
            {"type": "b", "color": "w"},  # 5 (f1)
            {"type": "n", "color": "w"},  # 6 (g1)
            {"type": "r", "color": "w"},  # 7 (h1)
        ],
    ]


def create_initial_state():
    """Generates a complete, isolated game room schema."""
    return {
        "players": {
            "white": None,
            "black": None,
        },  # Dynamic seating inside the DB payload
        "bot": {
            "enabled": False,
            "color": None,
        },
        "current_turn": "white",
        "board": create_initial_board(),
        "castling_rights": {
            "w": {
                "king_has_moved": False,
                "a_rook_has_moved": False,
                "h_rook_has_moved": False,
            },
            "b": {
                "king_has_moved": False,
                "a_rook_has_moved": False,
                "h_rook_has_moved": False,
            },
        },
        "status": "active",  # "active" | "completed"
        "winner": None,  # None | "white" | "black" | "draw"
        "check_status": None,  # None | "white" | "black"
    }


def _bot_color(game_state):
    bot = game_state.get("bot", {})
    if not bot.get("enabled"):
        return None
    return bot.get("color")


def _bot_seat_reserved(game_state, color: str) -> bool:
    return _bot_color(game_state) == color and game_state["players"].get(color) is None


async def _persist_move_update(
    room_code,
    redis_room_key,
    game_state,
    result,
    move_from,
    move_to,
):
    def _as_coords(square):
        if isinstance(square, dict):
            return (square.get("row"), square.get("col"))
        return square

    await redis.set(redis_room_key, json.dumps(game_state))

    if game_state.get("status") == "completed" and "game_id" in game_state:
        try:
            final_position = final_fen(game_state)

            asyncio.create_task(
                asyncio.to_thread(
                    games_repo.complete_game,
                    game_state["game_id"],
                    game_state["winner"],
                    final_position,
                )
            )

        except (RuntimeError, ValueError, TypeError, KeyError, OSError) as e:
            print(
                f"[HISTORY WARN] failed to persist "
                f"completion for Room [{room_code}]: {e}"
            )

    async def _persist_move_and_log(
        game_id,
        auth_state,
        from_sq,
        to_sq,
        promotion,
        room_code,
    ):
        try:
            res = await asyncio.to_thread(
                record_move,
                game_id,
                auth_state,
                from_sq,
                to_sq,
                promotion,
            )

            print(
                f"[HISTORY] persisted move "
                f"id={res.get('id')} "
                f"ply={res.get('ply')} "
                f"room={room_code}"
            )

        except (RuntimeError, ValueError, TypeError, KeyError, OSError) as e:
            print(f"[HISTORY ERR] failed to persist move for Room [{room_code}]: {e}")

    try:
        if "game_id" in game_state and result.pre_move_state is not None:
            asyncio.create_task(
                _persist_move_and_log(
                    game_state["game_id"],
                    result.pre_move_state,
                    _as_coords(move_from),
                    _as_coords(move_to),
                    None,
                    room_code,
                )
            )

    except RuntimeError as e:
        print(
            f"[HISTORY WARN] failed to schedule persistence for Room [{room_code}]: {e}"
        )

    print(
        f"[SOCKET] Broadcasting match validation update to room pipe: {redis_room_key}"
    )

    await sio.emit(
        "move_executed",
        {
            "board": game_state["board"],
            "current_turn": game_state["current_turn"],
            "status": game_state["status"],
            "winner": game_state["winner"],
            "check_status": game_state["check_status"],
            "last_move": {
                "from": move_from,
                "to": move_to,
            },
        },
        to=redis_room_key,
    )


# --- API HTTP LAYER ---
@app.get("/")
async def root():
    return {"status": "online", "service": "chess-multiplayer-backend"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@app.get("/games/{game_id}/replay", response_model=ReplayDocument)
async def get_game_replay(game_id: str):
    try:
        doc = await asyncio.to_thread(replay_service.get_replay_document, game_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="game not found")
    return doc


@app.get("/games")
async def list_games(source_type: str | None = None, limit: int = 50):
    try:
        docs = await asyncio.to_thread(games_repo.list_games, source_type, limit)
        return docs
    except (RuntimeError, ValueError, OSError) as e:
        # Log a full traceback to the server console for debugging
        tb = traceback.format_exc()
        print("[ERROR] list_games failure:\n", tb)
        # Surface the error message in the response for local dev visibility
        raise HTTPException(status_code=500, detail=f"unable to list games: {e}")


@app.post("/games/import/pgn", response_model=ImportResponse)
async def import_pgn(
    request: Request,
    file: UploadFile | None = IMPORT_PGN_FILE,
    text: str | None = IMPORT_PGN_TEXT,
):
    """Import PGN via file upload or raw text.

    Accepts either a multipart file (`.pgn`) or a JSON/RAW body `text` field.
    Returns an import summary describing imported and failed games.
    """
    # If a file was uploaded, read it first and avoid re-reading the request
    # body (which is already consumed for multipart requests).
    source_filename = None
    if file is not None:
        source_filename = file.filename
        try:
            raw = await file.read()
            text = raw.decode("utf-8", errors="replace")
        finally:
            await file.close()

    # If `text` is still not provided, try to parse JSON bodies or raw text.
    if text is None:
        try:
            payload = await request.json()
            if isinstance(payload, dict) and "text" in payload:
                text = payload.get("text")
            elif isinstance(payload, str):
                text = payload
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError, TypeError):
            raw = await request.body()
            text = raw.decode("utf-8", errors="replace").strip() or None

    if file is None and (text is None or text.strip() == ""):
        raise HTTPException(status_code=400, detail="Provide a .pgn file or PGN text")

    try:
        result = await asyncio.to_thread(import_pgn_text, text, source_filename)
    except (RuntimeError, ValueError, TypeError, KeyError, OSError) as e:
        tb = traceback.format_exc()
        print("[ERROR] import_pgn failure:\n", tb)
        raise HTTPException(status_code=500, detail=f"import failed: {e}")

    return result


# --- TRANSIT HANDSHAKE ---
@sio.event
async def connect(sid, environ, auth):
    print(f"[CONNECT] Transport established for SID: {sid}")

    user_id = None
    if auth and "userId" in auth:
        user_id = auth["userId"]
        print(f"[IDENTITY] Handshake authenticated user token: {user_id}")
    else:
        print(
            "[IDENTITY WARNING] Client connected without an identity token. Rejecting connection."
        )
        return False

    await sio.save_session(sid, {"user_id": user_id, "room_id": None})


# --- LOBBY CHANNEL ORCHESTRATION ---
@sio.on("join_room")
async def handle_join_room(sid, data):
    room_code = data.get("roomId", "").strip().upper()
    if not room_code or len(room_code) != 4:
        print(f"[ROOM REJECTED] SID [{sid}] provided an invalid code: {room_code}")
        return

    redis_room_key = f"room:{room_code}"

    session = await sio.get_session(sid)
    user_id = session.get("user_id")

    await sio.save_session(sid, {"user_id": user_id, "room_id": room_code})
    await sio.enter_room(sid, redis_room_key)
    print(f"[ROOM JOIN] SID [{sid}] entered network channel: {redis_room_key}")

    raw_state = await redis.get(redis_room_key)
    if not raw_state:
        game_state = create_initial_state()
        print(f"[ROOM PROVISION] Initialized empty state cache for Room [{room_code}]")
    else:
        game_state = json.loads(raw_state)

    players = game_state["players"]

    if players["white"] == user_id:
        role = "white"
        print(
            f"[SLOT RECLAIM] User [{user_id}] returned to White in Room [{room_code}]."
        )
    elif players["black"] == user_id:
        role = "black"
        print(
            f"[SLOT RECLAIM] User [{user_id}] returned to Black in Room [{room_code}]."
        )
    elif players["white"] is None:
        players["white"] = user_id
        role = "white"
        print(f"[SLOT CLAIM] User [{user_id}] claimed White in Room [{room_code}].")
    elif players["black"] is None and not _bot_seat_reserved(game_state, "black"):
        players["black"] = user_id
        role = "black"
        print(f"[SLOT CLAIM] User [{user_id}] claimed Black in Room [{room_code}].")
    else:
        role = "spectator"
        print(
            f"[SLOT SPECTATE] User [{user_id}] joined Room [{room_code}] as Spectator."
        )

    await redis.set(redis_room_key, json.dumps(game_state))

    await sio.emit(
        "assigned_role",
        {
            "room_id": room_code,
            "color": role,
            "board": game_state["board"],
            "current_turn": game_state["current_turn"],
            "status": game_state.get("status", "active"),
            "winner": game_state.get("winner", None),
            "check_status": game_state.get("check_status", None),
        },
        to=sid,
    )


@sio.on("create_room")
async def handle_create_room(sid, data=None):
    """Create a new 4-letter room code, provision state, and assign the creator a seat."""
    session = await sio.get_session(sid)
    user_id = session.get("user_id") if session else None
    if not user_id:
        print(
            f"[CREATE REJECT] SID [{sid}] missing user identity during room creation."
        )
        return

    # Generate a unique 4-letter room code
    def gen_code():
        return "".join(random.choice(string.ascii_uppercase) for _ in range(4))

    room_code = gen_code()
    attempt = 0
    while attempt < 10:
        redis_key = f"room:{room_code}"
        existing = await redis.get(redis_key)
        if not existing:
            break
        room_code = gen_code()
        attempt += 1

    redis_room_key = f"room:{room_code}"
    game_state = create_initial_state()
    # Assign creator to white by default
    game_state["players"]["white"] = user_id

    # Create a durable game record for this live room
    try:
        game_id = await asyncio.to_thread(
            create_game_record, room_code, "startpos", "live"
        )
        game_state["game_id"] = game_id
    except (RuntimeError, ValueError, TypeError, KeyError, OSError) as e:
        print(
            f"[WARN] Could not create durable game record for Room [{room_code}]: {e}"
        )

    await redis.set(redis_room_key, json.dumps(game_state))
    await sio.save_session(sid, {"user_id": user_id, "room_id": room_code})
    await sio.enter_room(sid, redis_room_key)

    print(f"[ROOM CREATED] User [{user_id}] created Room [{room_code}].")

    await sio.emit(
        "assigned_role",
        {
            "room_id": room_code,
            "color": "white",
            "board": game_state["board"],
            "current_turn": game_state["current_turn"],
            "status": game_state.get("status", "active"),
            "winner": game_state.get("winner", None),
            "check_status": game_state.get("check_status", None),
        },
        to=sid,
    )


@sio.on("create_bot_room")
async def handle_create_bot_room(sid, data=None):
    session = await sio.get_session(sid)
    user_id = session.get("user_id") if session else None
    if not user_id:
        print(
            f"[CREATE REJECT] SID [{sid}] missing user identity during bot room creation."
        )
        return

    def gen_code():
        return "".join(random.choice(string.ascii_uppercase) for _ in range(4))

    room_code = gen_code()
    attempt = 0
    while attempt < 10:
        redis_key = f"room:{room_code}"
        existing = await redis.get(redis_key)
        if not existing:
            break
        room_code = gen_code()
        attempt += 1

    redis_room_key = f"room:{room_code}"
    game_state = create_initial_state()
    game_state["players"]["white"] = user_id
    game_state["bot"] = {"enabled": True, "color": "black"}

    try:
        game_id = await asyncio.to_thread(
            create_game_record, room_code, "startpos", "bot"
        )
        game_state["game_id"] = game_id
    except (RuntimeError, ValueError, TypeError, KeyError, OSError) as e:
        print(
            f"[WARN] Could not create durable game record for Bot Room [{room_code}]: {e}"
        )

    await redis.set(redis_room_key, json.dumps(game_state))
    await sio.save_session(sid, {"user_id": user_id, "room_id": room_code})
    await sio.enter_room(sid, redis_room_key)

    print(f"[BOT ROOM CREATED] User [{user_id}] created Bot Room [{room_code}].")

    await sio.emit(
        "assigned_role",
        {
            "room_id": room_code,
            "color": "white",
            "board": game_state["board"],
            "current_turn": game_state["current_turn"],
            "status": game_state.get("status", "active"),
            "winner": game_state.get("winner", None),
            "check_status": game_state.get("check_status", None),
        },
        to=sid,
    )


# --- VALIDATION & ISOLATED REAL-TIME BROADCAST ---
@sio.on("propose_move")
async def handle_propose_move(sid, data):
    session = await sio.get_session(sid)
    if not session:
        return

    room_code = session.get("room_id")
    user_id = session.get("user_id")

    if not room_code:
        print(f"[REJECTED] SID [{sid}] attempted to move without a room assignment.")
        return

    redis_room_key = f"room:{room_code}"

    # 1. Fetch authoritative state
    raw_state = await redis.get(redis_room_key)

    if not raw_state:
        print(f"[ERROR] Active match state missing for Room {room_code}!")
        return

    game_state = json.loads(raw_state)

    # 2. Resolve player identity
    players = game_state["players"]

    player_color = (
        "white"
        if players["white"] == user_id
        else "black"
        if players["black"] == user_id
        else None
    )

    if player_color is None:
        print(f"[REJECTED] Room [{room_code}] - User is not an active player")

        await sio.emit(
            "move_rejected",
            {"reason": "You are not an active player"},
            to=sid,
        )
        return

    # 3. Extract proposed coordinates
    move_from = data.get("from")
    move_to = data.get("to")

    f_row = move_from["row"]
    f_col = move_from["col"]
    t_row = move_to["row"]
    t_col = move_to["col"]

    # 4. Execute through shared authoritative move service
    result = execute_move(
        game_state,
        player_color,
        f_row,
        f_col,
        t_row,
        t_col,
    )

    if not result.accepted:
        print(f"[REJECTED] Room [{room_code}] - {result.reason}")

        await sio.emit(
            "move_rejected",
            {"reason": result.reason},
            to=sid,
        )
        return

    game_state = result.game_state

    await _persist_move_update(
        room_code,
        redis_room_key,
        game_state,
        result,
        move_from,
        move_to,
    )

    bot_color = _bot_color(game_state)
    has_ml_player = hasattr(app.state, "ml_player")
    print(
        f"[BOT] Room [{room_code}] preflight status={game_state.get('status')} "
        f"current_turn={game_state.get('current_turn')} bot_color={bot_color} "
        f"ml_player_ready={has_ml_player}"
    )
    if (
        game_state.get("status") == "active"
        and bot_color is not None
        and game_state.get("current_turn") == bot_color
        and has_ml_player
    ):
        print(f"[BOT] Room [{room_code}] turn={bot_color} generating move")
        try:
            bot_move = generate_bot_move(game_state, app.state.ml_player)
            print(
                f"[BOT] Room [{room_code}] predicted from=({bot_move.from_row},{bot_move.from_col}) "
                f"to=({bot_move.to_row},{bot_move.to_col}) promotion={bot_move.promotion}"
            )
        except (RuntimeError, ValueError, TypeError, KeyError, OSError) as e:
            print(f"[BOT WARN] failed to generate move for Room [{room_code}]: {e}")
            return

        bot_result = execute_move(
            game_state,
            bot_color,
            bot_move.from_row,
            bot_move.from_col,
            bot_move.to_row,
            bot_move.to_col,
        )

        if not bot_result.accepted:
            print(f"[BOT REJECTED] Room [{room_code}] reason={bot_result.reason}")

            await sio.emit(
                "bot_move_rejected",
                {
                    "room_id": room_code,
                    "reason": bot_result.reason,
                    "from": {
                        "row": bot_move.from_row,
                        "col": bot_move.from_col,
                    },
                    "to": {
                        "row": bot_move.to_row,
                        "col": bot_move.to_col,
                    },
                },
                to=redis_room_key,
            )
            return

        print(
            f"[BOT ACCEPTED] Room [{room_code}] from=({bot_move.from_row},{bot_move.from_col}) "
            f"to=({bot_move.to_row},{bot_move.to_col})"
        )

        game_state = bot_result.game_state
        await _persist_move_update(
            room_code,
            redis_room_key,
            game_state,
            bot_result,
            {"row": bot_move.from_row, "col": bot_move.from_col},
            {"row": bot_move.to_row, "col": bot_move.to_col},
        )


@sio.event
async def disconnect(sid):
    print(f"[DISCONNECT] Client transport link severed for SID: {sid}")
