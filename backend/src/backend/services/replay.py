from typing import Dict

from ..repositories import games as games_repo
from ..repositories import game_moves as moves_repo


def get_replay_document(game_id: str) -> Dict:
    """Assemble a replay document for `game_id`.

    Raises ValueError if game not found.
    """
    game = games_repo.get_game(game_id)
    if not game:
        raise ValueError("game not found")

    moves = moves_repo.get_moves_for_game(game_id)

    # Prepend a synthetic ply-0 move that represents the initial position.
    # This makes the replay document uniformly addressable by ply where 0
    # is the starting board and subsequent plies are the persisted moves.
    initial_fen = game.get("initial_fen")
    initial_created = game.get("created_at")
    ply0 = {
        "ply": 0,
        "san": "",
        "fen_after": initial_fen,
        "from_square": None,
        "to_square": None,
        "promotion": None,
        "created_at": initial_created,
    }

    moves_with_initial = [ply0] + moves

    # Normalize the document shape expected by the API schema
    doc = {
        "game_id": game.get("id"),
        "room_code": game.get("room_code"),
        "source_type": game.get("source_type"),
        "initial_fen": initial_fen,
        "final_fen": game.get("final_fen"),
        "status": game.get("status"),
        "result": game.get("result"),
        "started_at": game.get("started_at"),
        "completed_at": game.get("completed_at"),
        "created_at": game.get("created_at"),
        "updated_at": game.get("updated_at"),
        "moves": moves_with_initial,
    }

    return doc
