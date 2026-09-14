import chess
from chess_ml.inference import MovePrediction
from main import create_initial_state
from services.bot_move import (
    BotMove,
    generate_bot_move,
    square_to_coords,
)


class FakeMLPlayer:
    def __init__(self):
        self.received_fen = None

    def predict_move(self, fen: str) -> MovePrediction:
        self.received_fen = fen

        return MovePrediction(
            from_square="e2",
            to_square="e4",
            promotion=None,
            score=0.75,
            model_version="test-model",
        )


def test_square_to_coords():
    assert square_to_coords("a8") == (0, 0)
    assert square_to_coords("h8") == (0, 7)
    assert square_to_coords("a1") == (7, 0)
    assert square_to_coords("h1") == (7, 7)
    assert square_to_coords("e2") == (6, 4)
    assert square_to_coords("e4") == (4, 4)


def test_generate_bot_move_from_initial_state():
    game_state = create_initial_state()

    assert game_state["bot"] == {"enabled": False, "color": None}

    ml_player = FakeMLPlayer()

    move = generate_bot_move(
        game_state,
        ml_player,
    )

    assert ml_player.received_fen == chess.STARTING_FEN

    assert move == BotMove(
        from_row=6,
        from_col=4,
        to_row=4,
        to_col=4,
        promotion=None,
    )
