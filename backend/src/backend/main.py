# backend/src/backend/main.py
import uvicorn
import socketio
from fastapi import FastAPI, Response
from backend.validator import is_legal_move

app = FastAPI()
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
asgi_app = socketio.ASGIApp(sio, other_asgi_app=app)

# --- TRACK 3: GLOBAL ENGINE GAME STATE ---
# Insert this full grid layout into your GAME_STATE inside backend/src/backend/main.py
GAME_STATE = {
    "players": {"white": None, "black": None},
    "current_turn": "white",
    "board": [
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
    ],
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


@app.get("/")
async def root():
    return {"status": "online", "service": "chess-multiplayer-backend"}


# --- HEALTH CHECK ENDPOINT ---
@app.get("/health")
async def health_check():
    """
    Explicit health status probe returning HTTP 200 OK.
    """
    return {"status": "healthy"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


# --- NETWORK LIFECYCLE EVENTS ---
@sio.event
async def connect(sid, environ):
    print(f"[SOCKET] Client connected: {sid}")

    # 1. Dynamically lock in the slots in memory immediately
    if GAME_STATE["players"]["white"] is None:
        GAME_STATE["players"]["white"] = sid
        role = "white"
        print(f"Slot Lock: {sid} is White")
    elif GAME_STATE["players"]["black"] is None:
        GAME_STATE["players"]["black"] = sid
        role = "black"
        print(f"Slot Lock: {sid} is Black")
    else:
        role = "spectator"
        print(f"Slot Lock: {sid} is Spectator")

    # 2. PROACTIVE INITIALIZATION: Push the state immediately to the connecting player
    print(
        f"[ROLE DISPATCH] Proactively pushing role '{role}' and matrix to SID [{sid}]"
    )
    await sio.emit(
        "assigned_role",
        {
            "color": role,
            "board": GAME_STATE["board"],
            "current_turn": GAME_STATE["current_turn"],
        },
        to=sid,  # Target explicitly only this specific browser session
    )


# Authoritative Role Dispatcher
@sio.on("request_role")
async def handle_request_role(sid):
    if GAME_STATE["players"]["white"] == sid:
        role = "white"
    elif GAME_STATE["players"]["black"] == sid:
        role = "black"
    else:
        role = "spectator"

    print(
        f"[ROLE DISPATCH] Sending stable role confirmation '{role}' and current board snapshot to SID [{sid}]"
    )

    # Send BOTH the role identity and the current state of the game
    await sio.emit(
        "assigned_role",
        {
            "color": role,
            "board": GAME_STATE["board"],
            "current_turn": GAME_STATE["current_turn"],
        },
        to=sid,
    )


@sio.event
async def disconnect(sid):
    print(f"[SOCKET] Client disconnected: {sid}")
    if GAME_STATE["players"]["white"] == sid:
        GAME_STATE["players"]["white"] = None
        print("White slot is now vacant.")
    elif GAME_STATE["players"]["black"] == sid:
        GAME_STATE["players"]["black"] = None
        print("Black slot is now vacant.")


# --- TRACK 3: VALIDATION & TRACK 4: REAL-TIME BROADCAST ---
@sio.on("propose_move")
async def handle_propose_move(sid, data):
    print(f"[SOCKET] Move proposed from SID [{sid}]: {data}")

    # 1. Identity & Turn Check
    player_color = (
        "white"
        if GAME_STATE["players"]["white"] == sid
        else "black"
        if GAME_STATE["players"]["black"] == sid
        else None
    )
    if player_color is None or player_color != GAME_STATE["current_turn"]:
        print(f"[REJECTED] Out of turn or unauthorized: {player_color}")
        await sio.emit("move_rejected", {"reason": "Not your turn"}, to=sid)
        return

    # 2. Extract coordinates
    move_from = data.get("from")
    move_to = data.get("to")

    f_row, f_col = move_from["row"], move_from["col"]
    t_row, t_col = move_to["row"], move_to["col"]

    # TRACK 3: GEOMETRIC RULES ENGINE VALIDATION
    if not is_legal_move(
        GAME_STATE["board"], f_row, f_col, t_row, t_col, GAME_STATE["castling_rights"]
    ):
        print(
            f"[REJECTED] Geometric Rule Violation from [{f_row}][{f_col}] to [{t_row}][{t_col}]"
        )
        await sio.emit("move_rejected", {"reason": "Illegal chess movement"}, to=sid)
        return

    # 3. Authoritative Python State Mutation (Only runs if validator returned True)
    moving_piece = GAME_STATE["board"][f_row][f_col]
    if moving_piece:
        p_type = moving_piece["type"]
        p_color = moving_piece["color"]

        # CHECK FOR SPECIAL ORCHESTRATION: King Castling Slide
        if p_type == "k" and abs(t_col - f_col) == 2:
            home_rank = 0 if p_color == "w" else 7
            is_kingside = t_col > f_col

            # Identify source and destination of the castling Rook
            old_rook_col = 7 if is_kingside else 0
            new_rook_col = 5 if is_kingside else 3

            # Snap-move the Rook programmatically
            rook_piece = GAME_STATE["board"][home_rank][old_rook_col]
            GAME_STATE["board"][home_rank][new_rook_col] = rook_piece
            GAME_STATE["board"][home_rank][old_rook_col] = None

        # UPDATE HISTORICAL CASTLING RIGHTS ON ANY RELEVANT PIECE MOVE
        rights = GAME_STATE["castling_rights"][p_color]
        if p_type == "k":
            rights["king_has_moved"] = True
        elif p_type == "r":
            if f_col == 0:
                rights["a_rook_has_moved"] = True
            elif f_col == 7:
                rights["h_rook_has_moved"] = True

        # Standard physical position update for the primary moving piece
        GAME_STATE["board"][t_row][t_col] = moving_piece
        GAME_STATE["board"][f_row][f_col] = None

    # 4. Advance Turn Switch
    GAME_STATE["current_turn"] = "black" if player_color == "white" else "white"

    # 5. Broadcast Full State Snapshot
    print("[SOCKET] Broadcasting full authoritative board state to clients...")
    await sio.emit(
        "move_executed",
        {
            "board": GAME_STATE["board"],
            "current_turn": GAME_STATE["current_turn"],
            "last_move": {"from": move_from, "to": move_to},
        },
    )


def main():
    uvicorn.run("backend.main:asgi_app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
