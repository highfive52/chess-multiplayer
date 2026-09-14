import asyncio
import copy
import json

import main
import pytest
from main import create_initial_state
from services.bot_move import BotMove
from services.game_move import MoveResult


class FakeRedis:
    def __init__(self, initial=None):
        self.store = dict(initial or {})

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value):
        self.store[key] = value


class FakeSio:
    def __init__(self, sessions=None):
        self.sessions = dict(sessions or {})
        self.emitted = []
        self.entered = []
        self.saved = []

    async def get_session(self, sid):
        return self.sessions.get(sid, {})

    async def save_session(self, sid, data):
        self.saved.append((sid, data))
        self.sessions[sid] = data

    async def enter_room(self, sid, room):
        self.entered.append((sid, room))

    async def emit(self, event, payload, to=None):
        self.emitted.append((event, payload, to))


@pytest.mark.anyio
async def test_create_bot_room_assigns_white_and_reserves_black(monkeypatch):
    fake_redis = FakeRedis()
    fake_sio = FakeSio({"sid-1": {"user_id": "user-1"}})
    created_games = []

    monkeypatch.setattr(main, "redis", fake_redis)
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(
        main, "create_game_record", lambda *args: created_games.append(args) or "game-1"
    )
    monkeypatch.setattr(main.random, "choice", lambda seq: "A")

    await main.handle_create_bot_room("sid-1", None)

    room_state = json.loads(fake_redis.store["room:AAAA"])

    assert room_state["players"] == {"white": "user-1", "black": None}
    assert room_state["bot"] == {"enabled": True, "color": "black"}
    assert room_state["game_id"] == "game-1"
    assert created_games == [("AAAA", "startpos", "bot")]
    assert fake_sio.emitted[0][0] == "assigned_role"
    assert fake_sio.emitted[0][1]["color"] == "white"


@pytest.mark.anyio
async def test_join_room_keeps_human_out_of_bot_seat(monkeypatch):
    room_state = create_initial_state()
    room_state["players"]["white"] = "creator"
    room_state["bot"] = {"enabled": True, "color": "black"}

    fake_redis = FakeRedis({"room:ABCD": json.dumps(room_state)})
    fake_sio = FakeSio({"sid-2": {"user_id": "user-2"}})

    monkeypatch.setattr(main, "redis", fake_redis)
    monkeypatch.setattr(main, "sio", fake_sio)

    await main.handle_join_room("sid-2", {"roomId": "abcd"})

    updated_state = json.loads(fake_redis.store["room:ABCD"])

    assert updated_state["players"] == {"white": "creator", "black": None}
    assert fake_sio.emitted[0][0] == "assigned_role"
    assert fake_sio.emitted[0][1]["color"] == "spectator"


@pytest.mark.anyio
async def test_human_move_triggers_bot_reply(monkeypatch):
    room_state = create_initial_state()
    room_state["players"]["white"] = "user-1"
    room_state["bot"] = {"enabled": True, "color": "black"}
    room_state["game_id"] = "game-1"

    fake_redis = FakeRedis({"room:ABCD": json.dumps(room_state)})
    fake_sio = FakeSio({"sid-3": {"user_id": "user-1", "room_id": "ABCD"}})

    execute_calls = []
    persist_calls = []
    bot_calls = []

    async def fake_persist(
        room_code, redis_room_key, game_state, result, move_from, move_to
    ):
        fake_redis.store[redis_room_key] = json.dumps(game_state)
        persist_calls.append(
            (
                room_code,
                redis_room_key,
                copy.deepcopy(game_state),
                move_from,
                move_to,
            )
        )

    def fake_execute_move(game_state, player_color, from_row, from_col, to_row, to_col):
        execute_calls.append((player_color, from_row, from_col, to_row, to_col))
        pre_move_state = {
            "board": copy.deepcopy(game_state["board"]),
            "current_turn": game_state["current_turn"],
            "castling_rights": copy.deepcopy(game_state["castling_rights"]),
        }

        if player_color == "white":
            game_state["current_turn"] = "black"
        else:
            game_state["current_turn"] = "white"

        return MoveResult(True, None, game_state, pre_move_state)

    def fake_generate_bot_move(game_state, ml_player):
        bot_calls.append((game_state["current_turn"], ml_player))
        return BotMove(
            from_row=1,
            from_col=4,
            to_row=3,
            to_col=4,
            promotion=None,
        )

    monkeypatch.setattr(main, "redis", fake_redis)
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "_persist_move_update", fake_persist)
    monkeypatch.setattr(main, "execute_move", fake_execute_move)
    monkeypatch.setattr(main, "generate_bot_move", fake_generate_bot_move)
    monkeypatch.setattr(main.app.state, "ml_player", object(), raising=False)

    await main.handle_propose_move(
        "sid-3",
        {
            "from": {"row": 6, "col": 4},
            "to": {"row": 4, "col": 4},
        },
    )

    assert execute_calls == [
        ("white", 6, 4, 4, 4),
        ("black", 1, 4, 3, 4),
    ]
    assert len(persist_calls) == 2
    assert persist_calls[0][2]["current_turn"] == "black"
    assert persist_calls[1][2]["current_turn"] == "white"
    assert bot_calls == [("black", main.app.state.ml_player)]


@pytest.mark.anyio
async def test_illegal_bot_prediction_leaves_game_on_black_turn(monkeypatch):
    room_state = create_initial_state()
    room_state["players"]["white"] = "user-1"
    room_state["bot"] = {"enabled": True, "color": "black"}
    room_state["game_id"] = "game-1"

    fake_redis = FakeRedis({"room:ABCD": json.dumps(room_state)})
    fake_sio = FakeSio({"sid-4": {"user_id": "user-1", "room_id": "ABCD"}})

    persist_calls = []
    execute_calls = []

    async def fake_persist(
        room_code, redis_room_key, game_state, result, move_from, move_to
    ):
        fake_redis.store[redis_room_key] = json.dumps(game_state)
        persist_calls.append(
            (
                room_code,
                redis_room_key,
                copy.deepcopy(game_state),
                result.accepted,
                move_from,
                move_to,
            )
        )

    def fake_execute_move(game_state, player_color, from_row, from_col, to_row, to_col):
        execute_calls.append((player_color, from_row, from_col, to_row, to_col))
        pre_move_state = {
            "board": copy.deepcopy(game_state["board"]),
            "current_turn": game_state["current_turn"],
            "castling_rights": copy.deepcopy(game_state["castling_rights"]),
        }

        if player_color == "white":
            game_state["current_turn"] = "black"
            return MoveResult(True, None, game_state, pre_move_state)

        return MoveResult(
            False, "Move leaves your king in check", game_state, pre_move_state
        )

    monkeypatch.setattr(main, "redis", fake_redis)
    monkeypatch.setattr(main, "sio", fake_sio)
    monkeypatch.setattr(main, "_persist_move_update", fake_persist)
    monkeypatch.setattr(main, "execute_move", fake_execute_move)
    monkeypatch.setattr(
        main, "generate_bot_move", lambda *args: BotMove(0, 3, 4, 7, None)
    )
    monkeypatch.setattr(main.app.state, "ml_player", object(), raising=False)

    await main.handle_propose_move(
        "sid-4",
        {
            "from": {"row": 6, "col": 4},
            "to": {"row": 4, "col": 4},
        },
    )

    updated_state = json.loads(fake_redis.store["room:ABCD"])

    assert execute_calls == [
        ("white", 6, 4, 4, 4),
        ("black", 0, 3, 4, 7),
    ]
    assert len(persist_calls) == 1
    assert persist_calls[0][2]["current_turn"] == "black"
    assert updated_state["current_turn"] == "black"
    assert updated_state["status"] == "active"


@pytest.mark.anyio
async def test_bot_finishing_move_persists_completion(monkeypatch):
    fake_redis = FakeRedis()
    completed_calls = []
    record_calls = []
    tasks = []

    real_create_task = asyncio.create_task

    def fake_create_task(coro):
        task = real_create_task(coro)
        tasks.append(task)
        return task

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(main, "redis", fake_redis)
    monkeypatch.setattr(main.asyncio, "create_task", fake_create_task)
    monkeypatch.setattr(main.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(
        main.games_repo, "complete_game", lambda *args: completed_calls.append(args)
    )
    monkeypatch.setattr(
        main,
        "record_move",
        lambda *args: record_calls.append(args) or {"id": "move-1", "ply": 2},
    )
    monkeypatch.setattr(main, "final_fen", lambda game_state: "final-fen")

    game_state = create_initial_state()
    game_state["players"]["white"] = "user-1"
    game_state["bot"] = {"enabled": True, "color": "black"}
    game_state["game_id"] = "game-1"
    game_state["status"] = "completed"
    game_state["winner"] = "black"
    game_state["current_turn"] = "white"

    result = MoveResult(
        accepted=True,
        reason=None,
        game_state=game_state,
        pre_move_state={
            "board": copy.deepcopy(game_state["board"]),
            "current_turn": "black",
            "castling_rights": copy.deepcopy(game_state["castling_rights"]),
        },
    )

    await main._persist_move_update(
        "FXSO",
        "room:FXSO",
        game_state,
        result,
        {"row": 1, "col": 4},
        {"row": 3, "col": 4},
    )

    await asyncio.gather(*tasks)

    assert completed_calls == [("game-1", "black", "final-fen")]
    assert len(record_calls) == 1
