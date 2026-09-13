"""Move encoding for the chess policy model."""

from __future__ import annotations

import chess

# Current board
#      ↓
# encode_board()
#      ↓
# 18 × 8 × 8 tensor
#      ↓
# CNN
#      ↓
# scores across 20,480 move classes
#      ↓
# choose predicted class
#      ↓
# 405
#      ↓
# decode_move()
#      ↓
# chess.Move("g1f3")
#      ↓
# convert to game-engine coordinates
#      ↓
# {"from": "g1", "to": "f3", "promotion": null}
#      ↓
# existing game validator


SQUARE_COUNT = 64
BASE_MOVE_COUNT = SQUARE_COUNT * SQUARE_COUNT

PROMOTION_TO_INDEX = {
    None: 0,
    chess.KNIGHT: 1,
    chess.BISHOP: 2,
    chess.ROOK: 3,
    chess.QUEEN: 4,
}

INDEX_TO_PROMOTION = {
    index: promotion for promotion, index in PROMOTION_TO_INDEX.items()
}

MOVE_CLASS_COUNT = len(PROMOTION_TO_INDEX) * BASE_MOVE_COUNT


def encode_move(move: chess.Move) -> int:
    """Encode a chess move as a stable integer class ID."""

    promotion_index = PROMOTION_TO_INDEX.get(move.promotion)

    if promotion_index is None:
        raise ValueError(f"Unsupported promotion piece: {move.promotion}")

    base_move_id = move.from_square * SQUARE_COUNT + move.to_square

    return promotion_index * BASE_MOVE_COUNT + base_move_id


def decode_move(move_id: int) -> chess.Move:
    """Decode an integer class ID into a chess move."""

    if not 0 <= move_id < MOVE_CLASS_COUNT:
        raise ValueError(
            f"Move ID must be between 0 and {MOVE_CLASS_COUNT - 1}: {move_id}"
        )

    promotion_index, base_move_id = divmod(
        move_id,
        BASE_MOVE_COUNT,
    )

    from_square, to_square = divmod(
        base_move_id,
        SQUARE_COUNT,
    )

    promotion = INDEX_TO_PROMOTION[promotion_index]

    return chess.Move(
        from_square=from_square,
        to_square=to_square,
        promotion=promotion,
    )
