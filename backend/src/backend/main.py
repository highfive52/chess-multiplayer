import json
import os
from fastapi import FastAPI, Response
import socketio
import redis.asyncio as aioredis
from backend.validator import (
    is_legal_move,
    find_king,
    is_square_attacked,
    causes_self_check,
    has_legal_moves,
)
import random
import string

# 1. Configure the Redis connection string (Defaulting to Docker localhost)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis = aioredis.from_url(REDIS_URL, decode_responses=True)

# 2. Setup Socket.io and FastAPI boundaries
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = FastAPI()
asgi_app = socketio.ASGIApp(sio, app)


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
    elif players["black"] is None:
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

    # 1. FETCH Authoritative state
    raw_state = await redis.get(redis_room_key)
    if not raw_state:
        print(f"[ERROR] Active match state missing for Room {room_code}!")
        return
    game_state = json.loads(raw_state)

    # 🛑 CHECKPOINT A: Block matching on completed timelines
    if game_state.get("status") == "completed":
        await sio.emit(
            "move_rejected",
            {"reason": "The game has already ended in checkmate."},
            to=sid,
        )
        return

    # 2. Identity & Turn Validation
    players = game_state["players"]
    player_color = (
        "white"
        if players["white"] == user_id
        else "black"
        if players["black"] == user_id
        else None
    )

    if player_color is None or player_color != game_state["current_turn"]:
        print(
            f"[REJECTED] Room [{room_code}] - Move out of turn from color: {player_color}"
        )
        await sio.emit("move_rejected", {"reason": "Not your turn"}, to=sid)
        return

    opponent_color = "black" if player_color == "white" else "white"

    # 3. Extract coordinates
    move_from = data.get("from")
    move_to = data.get("to")
    f_row, f_col = move_from["row"], move_from["col"]
    t_row, t_col = move_to["row"], move_to["col"]

    # GEOMETRIC RULES ENGINE VALIDATION
    if not is_legal_move(
        game_state["board"], f_row, f_col, t_row, t_col, game_state["castling_rights"]
    ):
        print(f"[REJECTED] Geometric Rule Violation in Room [{room_code}]")
        await sio.emit("move_rejected", {"reason": "Illegal chess movement"}, to=sid)
        return

    # 🛑 CHECKPOINT B: Block matching on Self-Exposing King moves (Illegal check avoidance)
    if causes_self_check(
        game_state["board"],
        player_color,
        f_row,
        f_col,
        t_row,
        t_col,
        game_state["castling_rights"],
    ):
        print(
            f"[REJECTED] Check Rule Violation: User leaves King exposed inside Room [{room_code}]"
        )
        await sio.emit(
            "move_rejected", {"reason": "Move leaves your king in check"}, to=sid
        )
        return

    # 4. State Mutation (Move verified safe)
    moving_piece = game_state["board"][f_row][f_col]
    if moving_piece:
        p_type = moving_piece["type"]
        p_color = moving_piece["color"]

        # King Castling Slide Check
        if p_type == "k" and abs(t_col - f_col) == 2:
            home_rank = 7 if p_color == "w" else 0
            is_kingside = t_col > f_col

            old_rook_col = 7 if is_kingside else 0
            new_rook_col = 5 if is_kingside else 3

            rook_piece = game_state["board"][home_rank][old_rook_col]
            game_state["board"][home_rank][new_rook_col] = rook_piece
            game_state["board"][home_rank][old_rook_col] = None

        # Update Castling Rights
        rights = game_state["castling_rights"][p_color]
        if p_type == "k":
            rights["king_has_moved"] = True
        elif p_type == "r":
            if f_col == 0:
                rights["a_rook_has_moved"] = True
            elif f_col == 7:
                rights["h_rook_has_moved"] = True

        game_state["board"][t_row][t_col] = moving_piece
        game_state["board"][f_row][f_col] = None

    # 🛑 CHECKPOINT C: Post-Move Check & Checkmate Evaluation
    opp_king_pos = find_king(game_state["board"], opponent_color)
    is_opp_in_check = is_square_attacked(
        game_state["board"],
        opp_king_pos[0],
        opp_king_pos[1],
        player_color,
        game_state["castling_rights"],
    )

    if is_opp_in_check:
        game_state["check_status"] = opponent_color
        print(
            f"[CONTEXT] {opponent_color} King placed into Check inside room {room_code}"
        )

        # Test if the checked player can legally move anywhere (Checkmate)
        if not has_legal_moves(
            game_state["board"], opponent_color, game_state["castling_rights"]
        ):
            game_state["status"] = "completed"
            game_state["winner"] = player_color
            print(f"[CHECKMATE] Room {room_code} finished. Winner: {player_color}")
    else:
        game_state["check_status"] = None

        # 🔄 FIX: Handle Stalemate Draws when player has zero moves left out of check
        if not has_legal_moves(
            game_state["board"], opponent_color, game_state["castling_rights"]
        ):
            game_state["status"] = "completed"
            game_state["winner"] = "draw"
            print(f"[STALEMATE] Room {room_code} finished in a draw.")

    # 5. Advance Turn only if match continues active
    if game_state["status"] == "active":
        game_state["current_turn"] = opponent_color

    # 6. SAVE Authoritative payload
    await redis.set(redis_room_key, json.dumps(game_state))

    # 7. BROADCAST updated status array downstream
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
            "last_move": {"from": move_from, "to": move_to},
        },
        to=redis_room_key,
    )


@sio.event
async def disconnect(sid):
    print(f"[DISCONNECT] Client transport link severed for SID: {sid}")
