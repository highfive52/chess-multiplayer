"""Board-state tensor encoding for the chess policy model."""

from __future__ import annotations

import chess
import torch


PIECE_CHANNELS = {
    (chess.WHITE, chess.PAWN): 0,
    (chess.WHITE, chess.KNIGHT): 1,
    (chess.WHITE, chess.BISHOP): 2,
    (chess.WHITE, chess.ROOK): 3,
    (chess.WHITE, chess.QUEEN): 4,
    (chess.WHITE, chess.KING): 5,
    (chess.BLACK, chess.PAWN): 6,
    (chess.BLACK, chess.KNIGHT): 7,
    (chess.BLACK, chess.BISHOP): 8,
    (chess.BLACK, chess.ROOK): 9,
    (chess.BLACK, chess.QUEEN): 10,
    (chess.BLACK, chess.KING): 11,
}


def encode_board(board: chess.Board) -> torch.Tensor:
    """Encode a chess board as an 18 x 8 x 8 float32 tensor."""

    # 18 × 8 × 8
    # ↑   ↑   ↑
    # │   │   └── files / columns
    # │   └────── ranks / rows
    # └────────── channels / feature planes

    tensor = torch.zeros(
        (18, 8, 8),
        dtype=torch.float32,
    )

    # Encode each occupied chess square into its piece channel.
    #
    # python-chess represents squares as integers from 0 through 63:
    #
    # a1 = 0
    # b1 = 1
    # ...
    # h1 = 7
    # a2 = 8
    # ...
    # h8 = 63
    #
    # piece_map() provides:
    #
    #     square -> chess.Piece
    #
    # The piece determines the tensor channel, while the square determines
    # the tensor row and column.
    #
    # Example:
    #
    #     white pawn on e2
    #         channel = 0
    #         rank = 1
    #         file = 4
    #
    #     tensor[0, 1, 4] = 1.0

    for square, piece in board.piece_map().items():
        channel = PIECE_CHANNELS[
            (piece.color, piece.piece_type)
        ]

        # Determine the rank (row) and file (column) of the square.
        rank = chess.square_rank(square)
        file = chess.square_file(square)

        tensor[channel, rank, file] = 1.0

    # White pawn channel — 0

    # rank 8    0 0 0 0 0 0 0 0
    # rank 7    0 0 0 0 0 0 0 0
    # rank 6    0 0 0 0 0 0 0 0
    # rank 5    0 0 0 0 0 0 0 0
    # rank 4    0 0 0 0 0 0 0 0
    # rank 3    0 0 0 0 0 0 0 0
    # rank 2    1 1 1 1 1 1 1 1
    # rank 1    0 0 0 0 0 0 0 0
    #           a b c d e f g h    

    if board.turn == chess.WHITE:
        tensor[12].fill_(1.0)

    if board.has_kingside_castling_rights(chess.WHITE):
        tensor[13].fill_(1.0)

    if board.has_queenside_castling_rights(chess.WHITE):
        tensor[14].fill_(1.0)

    if board.has_kingside_castling_rights(chess.BLACK):
        tensor[15].fill_(1.0)

    if board.has_queenside_castling_rights(chess.BLACK):
        tensor[16].fill_(1.0)

    if board.ep_square is not None:
        rank = chess.square_rank(board.ep_square)
        file = chess.square_file(board.ep_square)

        tensor[17, rank, file] = 1.0

    return tensor