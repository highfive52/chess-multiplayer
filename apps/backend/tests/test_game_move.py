from main import create_initial_state
from services.game_move import execute_move


def test_execute_move_applies_legal_move():
    game_state = create_initial_state()

    result = execute_move(
        game_state,
        player_color="white",
        from_row=6,
        from_col=4,
        to_row=4,
        to_col=4,
    )

    assert result.accepted is True
    assert result.reason is None

    assert result.game_state["board"][6][4] is None

    moved_piece = result.game_state["board"][4][4]
    assert moved_piece is not None
    assert moved_piece["type"] == "p"
    assert moved_piece["color"] == "w"

    assert result.game_state["current_turn"] == "black"

    assert result.pre_move_state is not None
    assert result.pre_move_state["board"][6][4]["type"] == "p"
    assert result.pre_move_state["board"][4][4] is None


def test_execute_move_rejects_out_of_turn_move():
    game_state = create_initial_state()

    result = execute_move(
        game_state,
        player_color="black",
        from_row=1,
        from_col=4,
        to_row=3,
        to_col=4,
    )

    assert result.accepted is False
    assert result.reason == "Not your turn"

    assert game_state["board"][1][4] is not None
    assert game_state["board"][3][4] is None
    assert game_state["current_turn"] == "white"


def test_execute_move_rejects_illegal_move():
    game_state = create_initial_state()

    result = execute_move(
        game_state,
        player_color="white",
        from_row=6,
        from_col=4,
        to_row=3,
        to_col=4,
    )

    assert result.accepted is False
    assert result.reason == "Illegal chess movement"

    assert game_state["board"][6][4] is not None
    assert game_state["board"][3][4] is None
    assert game_state["current_turn"] == "white"
