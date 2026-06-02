import json
import os
from fastapi import FastAPI, Response
import socketio
import redis.asyncio as aioredis
from backend.validator import is_legal_move

# 1. Configure the Redis connection string (Defaulting to Docker localhost)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis = aioredis.from_url(REDIS_URL, decode_responses=True)

# 2. Setup Socket.io and FastAPI boundaries
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = FastAPI()
asgi_app = socketio.ASGIApp(sio, app)

# Static Key for Milestone 1 & 2
GLOBAL_ROOM_KEY = "room:global"


def create_initial_board():
    return [
        # Row 0: White Major Pieces
        [
            {"type": "r", "color": "w"},
            {"type": "n", "color": "w"},
            {"type": "b", "color": "w"},
            {"type": "q", "color": "w"},
            {"type": "k", "color": "w"},
            {"type": "b", "color": "w"},
            {"type": "n", "color": "w"},
            {"type": "r", "color": "w"},
        ],
        # Row 1: White Pawns
        [{"type": "p", "color": "w"} for _ in range(8)],
        # Rows 2-5: Empty Spaces
        [None] * 8,
        [None] * 8,
        [None] * 8,
        [None] * 8,
        # Row 6: Black Pawns
        [{"type": "p", "color": "b"} for _ in range(8)],
        # Row 7: Black Major Pieces
        [
            {"type": "r", "color": "b"},
            {"type": "n", "color": "b"},
            {"type": "b", "color": "b"},
            {"type": "q", "color": "b"},
            {"type": "k", "color": "b"},
            {"type": "b", "color": "b"},
            {"type": "n", "color": "b"},
            {"type": "r", "color": "b"},
        ],
    ]


# Maps player slots directly to persistent localStorage UUID tokens
ACTIVE_PLAYERS = {"white": None, "black": None}


@app.get("/")
async def root():
    return {"status": "online", "service": "chess-multiplayer-backend"}


# --- HEALTH CHECK ENDPOINT ---
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@sio.event
async def connect(sid, environ, auth):
    print(f"[CONNECT] Transport link established for SID: {sid}")

    # Identity Extraction from Handshake Auth object (Aligned to frontend payload)
    user_id = None
    if auth and "userId" in auth:
        user_id = auth["userId"]
        print(f"[IDENTITY] Handshake authenticated user token: {user_id}")
    else:
        print(
            "[IDENTITY WARNING] Client connected without an identity token. Rejecting connection."
        )
        return False

    # Cache the user_id inside this specific socket's secure connection session context
    await sio.save_session(sid, {"user_id": user_id})

    # FETCH: Ask the Redis Model if a global match is already running
    raw_state = await redis.get(GLOBAL_ROOM_KEY)

    if not raw_state:
        game_state = {
            "board": create_initial_board(),
            "current_turn": "white",
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
        }
        await redis.set(GLOBAL_ROOM_KEY, json.dumps(game_state))
    else:
        game_state = json.loads(raw_state)

    # Dynamic Seat Assignment (Checking token presence rather than transient connection sid)
    if ACTIVE_PLAYERS["white"] == user_id:
        role = "white"
        print(f"[SLOT RECLAIM] User [{user_id}] reconnected and reclaimed White.")
    elif ACTIVE_PLAYERS["black"] == user_id:
        role = "black"
        print(f"[SLOT RECLAIM] User [{user_id}] reconnected and reclaimed Black.")
    elif ACTIVE_PLAYERS["white"] is None:
        ACTIVE_PLAYERS["white"] = user_id
        role = "white"
        print(f"[SLOT CLAIM] User [{user_id}] claimed empty White slot.")
    elif ACTIVE_PLAYERS["black"] is None:
        ACTIVE_PLAYERS["black"] = user_id
        role = "black"
        print(f"[SLOT CLAIM] User [{user_id}] claimed empty Black slot.")
    else:
        role = "spectator"
        print(f"[SLOT SPECTATE] User [{user_id}] connected as Spectator.")

    # Emit configuration directly back to the freshly connected view
    await sio.emit(
        "assigned_role",
        {
            "color": role,
            "board": game_state["board"],
            "current_turn": game_state["current_turn"],
        },
        to=sid,
    )


# Authoritative Role Dispatcher
@sio.on("request_role")
async def handle_request_role(sid):
    # FETCH: Pull the latest snapshot from Redis
    raw_state = await redis.get(GLOBAL_ROOM_KEY)
    if not raw_state:
        print("[ERROR] request_role failed: No active match state found in Redis!")
        return
    game_state = json.loads(raw_state)

    # Extract the user token cached on connection
    session = await sio.get_session(sid)
    user_id = session.get("user_id") if session else None

    if ACTIVE_PLAYERS["white"] == user_id:
        role = "white"
    elif ACTIVE_PLAYERS["black"] == user_id:
        role = "black"
    else:
        role = "spectator"

    print(f"[ROLE DISPATCH] Sending stable role confirmation '{role}' to SID [{sid}]")

    await sio.emit(
        "assigned_role",
        {
            "color": role,
            "board": game_state["board"],
            "current_turn": game_state["current_turn"],
        },
        to=sid,
    )


# --- TRACK 3: VALIDATION & TRACK 4: REAL-TIME BROADCAST ---
@sio.on("propose_move")
async def handle_propose_move(sid, data):
    print(f"[SOCKET] Move proposed from SID [{sid}]: {data}")

    # 1. FETCH: Pull the latest authoritative state from your Redis Model Layer
    raw_state = await redis.get(GLOBAL_ROOM_KEY)
    if not raw_state:
        print("[ERROR] No active match state found in Redis!")
        return
    game_state = json.loads(raw_state)

    # 2. Identity & Turn Check via session tokens
    session = await sio.get_session(sid)
    user_id = session.get("user_id") if session else None

    player_color = (
        "white"
        if ACTIVE_PLAYERS["white"] == user_id
        else "black"
        if ACTIVE_PLAYERS["black"] == user_id
        else None
    )

    if player_color is None or player_color != game_state["current_turn"]:
        print(f"[REJECTED] Out of turn or unauthorized: {player_color}")
        await sio.emit("move_rejected", {"reason": "Not your turn"}, to=sid)
        return

    # 3. Extract coordinates
    move_from = data.get("from")
    move_to = data.get("to")

    f_row, f_col = move_from["row"], move_from["col"]
    t_row, t_col = move_to["row"], move_to["col"]

    # TRACK 3: GEOMETRIC RULES ENGINE VALIDATION
    if not is_legal_move(
        game_state["board"], f_row, f_col, t_row, t_col, game_state["castling_rights"]
    ):
        print(
            f"[REJECTED] Geometric Rule Violation from [{f_row}][{f_col}] to [{t_row}][{t_col}]"
        )
        await sio.emit("move_rejected", {"reason": "Illegal chess movement"}, to=sid)
        return

    # 4. Authoritative State Mutation in Python memory
    moving_piece = game_state["board"][f_row][f_col]
    if moving_piece:
        p_type = moving_piece["type"]
        p_color = moving_piece["color"]

        # CHECK FOR SPECIAL ORCHESTRATION: King Castling Slide
        if p_type == "k" and abs(t_col - f_col) == 2:
            home_rank = 0 if p_color == "w" else 7
            is_kingside = t_col > f_col

            old_rook_col = 7 if is_kingside else 0
            new_rook_col = 5 if is_kingside else 3

            # Snap-move the Rook programmatically
            rook_piece = game_state["board"][home_rank][old_rook_col]
            game_state["board"][home_rank][new_rook_col] = rook_piece
            game_state["board"][home_rank][old_rook_col] = None

        # UPDATE HISTORICAL CASTLING RIGHTS
        rights = game_state["castling_rights"][p_color]
        if p_type == "k":
            rights["king_has_moved"] = True
        elif p_type == "r":
            if f_col == 0:
                rights["a_rook_has_moved"] = True
            elif f_col == 7:
                rights["h_rook_has_moved"] = True

        # Standard physical position update for the primary moving piece
        game_state["board"][t_row][t_col] = moving_piece
        game_state["board"][f_row][f_col] = None

    # 5. Advance Turn Switch
    game_state["current_turn"] = "black" if player_color == "white" else "white"

    # 6. SAVE: Lock the mutated snapshot back down to Redis
    await redis.set(GLOBAL_ROOM_KEY, json.dumps(game_state))

    # 7. Broadcast Full State Snapshot to the Views
    print("[SOCKET] Broadcasting full authoritative board state to clients...")
    await sio.emit(
        "move_executed",
        {
            "board": game_state["board"],
            "current_turn": game_state["current_turn"],
            "last_move": {"from": move_from, "to": move_to},
        },
    )


@sio.event
async def disconnect(sid):
    # Seats are preserved even when sockets close!
    print(f"[DISCONNECT] Client link severed temporarily for SID: {sid}")
