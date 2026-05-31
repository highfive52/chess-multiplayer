# backend/src/backend/validator.py


def is_legal_move(board, f_row, f_col, t_row, t_col) -> bool:
    """
    Main entry point for move validation.
    Checks basic bounds, piece existence, and coordinates piece-specific rules.
    """
    # 1. Bounds check (out of board limits)
    if not (0 <= f_row < 8 and 0 <= f_col < 8 and 0 <= t_row < 8 and 0 <= t_col < 8):
        return False

    # 2. Prevent moving to the exact same square
    if f_row == t_row and f_col == t_col:
        return False

    piece = board[f_row][f_col]
    if not piece:
        return False  # Can't move a non-existent piece

    target = board[t_row][t_col]
    # Prevent capturing your own color piece
    if target and target["color"] == piece["color"]:
        return False

    p_type = piece["type"]
    p_color = piece["color"]

    # Calculate displacement vectors
    row_diff = t_row - f_row
    col_diff = t_col - f_col

    # 3. Piece-Specific Geometric Dispatches
    if p_type == "n":  # KNIGHT: Must move in an L-shape (2x1 or 1x2)
        return (abs(row_diff) == 2 and abs(col_diff) == 1) or (
            abs(row_diff) == 1 and abs(col_diff) == 2
        )

    if p_type == "p":  # PAWN: Basic forward movement (Directional)
        direction = 1 if p_color == "w" else -1

        # Standard 1-square forward move to an empty square
        if col_diff == 0 and row_diff == direction and not target:
            return True

        # Initial 2-square forward move from starting ranks
        is_starting_rank = (f_row == 1 and p_color == "w") or (
            f_row == 6 and p_color == "b"
        )
        if col_diff == 0 and row_diff == 2 * direction and is_starting_rank:
            # Ensure the intermediate square is also clear
            intermediate_square = board[f_row + direction][f_col]
            if not intermediate_square and not target:
                return True

        # Standard diagonal capture
        if abs(col_diff) == 1 and row_diff == direction and target:
            return True

        return False

    # Temporary fallback for major pieces (r, b, q, k) until we write their vector loops
    return True
