import copy


def is_legal_move(board, f_row, f_col, t_row, t_col, castling_rights=None) -> bool:
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

    # Can't move a non-existent piece
    piece = board[f_row][f_col]
    if not piece:
        return False

    # Prevent capturing your own color piece
    target = board[t_row][t_col]
    if target and target["color"] == piece["color"]:
        return False

    p_type = piece["type"]
    p_color = piece["color"]

    # Calculate displacement vectors
    row_diff = t_row - f_row
    col_diff = t_col - f_col

    # 3. Piece-Specific Geometric Dispatches
    # KNIGHT: Must move in an L-shape (2x1 or 1x2)
    if p_type == "n":
        return (abs(row_diff) == 2 and abs(col_diff) == 1) or (
            abs(row_diff) == 1 and abs(col_diff) == 2
        )

    # PAWN: Basic forward movement (Directional)
    if p_type == "p":
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

    # ROOK: Straight lines only, no hopping
    if p_type == "r":
        if row_diff != 0 and col_diff != 0:
            return False  # Not a straight line

        step_row = 0 if row_diff == 0 else (1 if row_diff > 0 else -1)
        step_col = 0 if col_diff == 0 else (1 if col_diff > 0 else -1)

        curr_row = f_row + step_row
        curr_col = f_col + step_col

        while curr_row != t_row or curr_col != t_col:
            if board[curr_row][curr_col]:
                return False
            curr_row += step_row
            curr_col += step_col

        return True  # ◄ Explicitly return True here for consistency

    # BISHOP: Diagonals only, no hopping
    if p_type == "b":
        if abs(row_diff) != abs(col_diff):
            return False  # Not a perfect diagonal step

        step_row = 1 if row_diff > 0 else -1
        step_col = 1 if col_diff > 0 else -1

        curr_row = f_row + step_row
        curr_col = f_col + step_col

        while curr_row != t_row or curr_col != t_col:
            if board[curr_row][curr_col]:
                return False  # Diagonal line-of-sight is blocked!
            curr_row += step_row
            curr_col += step_col

        return True

    # QUEEN: Moves like a Rook OR a Bishop
    if p_type == "q":
        is_straight = row_diff == 0 or col_diff == 0
        is_diagonal = abs(row_diff) == abs(col_diff)

        if not (is_straight or is_diagonal):
            return False  # Invalid geometry

        step_row = 0 if row_diff == 0 else (1 if row_diff > 0 else -1)
        step_col = 0 if col_diff == 0 else (1 if col_diff > 0 else -1)

        curr_row = f_row + step_row
        curr_col = f_col + step_col

        while curr_row != t_row or curr_col != t_col:
            if board[curr_row][curr_col]:
                return False  # Path is blocked!
            curr_row += step_row
            curr_col += step_col

        return True

    # KING: Moves exactly 1 square in any direction
    if p_type == "k":
        # A. Standard 1-square movement in any direction
        if abs(row_diff) <= 1 and abs(col_diff) <= 1:
            return True

        # B. CASTLING ATTEMPT
        if row_diff == 0 and abs(col_diff) == 2:
            if not castling_rights:
                return False  # Safe fallback if rights aren't provided

            home_rank = 0 if p_color == "w" else 7
            if f_row != home_rank:
                return False

            if castling_rights[p_color]["king_has_moved"]:
                return False

            is_kingside = col_diff > 0
            rook_col = 7 if is_kingside else 0
            rook_flag = "h_rook_has_moved" if is_kingside else "a_rook_has_moved"

            if castling_rights[p_color][rook_flag]:
                return False

            potential_rook = board[home_rank][rook_col]
            if (
                not potential_rook
                or potential_rook["type"] != "r"
                or potential_rook["color"] != p_color
            ):
                return False

            start_col = min(f_col, rook_col) + 1
            end_col = max(f_col, rook_col)
            for c in range(start_col, end_col):
                if board[home_rank][c]:
                    return False

            return True

    return False  # ◄ Changed safety fallback to False for unhandled states


# --- 👑 CONTEXTUAL CHECK & SIMULATION UTILITIES ---


def find_king(board, color: str) -> tuple:
    """Locates the matrix coordinates of a specified king ('white' or 'black')."""
    target_char = "w" if color == "white" else "b"
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece and piece.get("type") == "k" and piece.get("color") == target_char:
                return (r, c)
    return None


def is_square_attacked(
    board,
    target_row: int,
    target_col: int,
    attacker_color: str,
    castling_rights: dict = None,
) -> bool:
    """Scans whether any active piece of attacker_color can legally hit the targeted coordinate."""
    attacker_char = "w" if attacker_color == "white" else "b"
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece and piece.get("color") == attacker_char:
                # Reuse geometric engine lookup to verify line of sight
                if is_legal_move(board, r, c, target_row, target_col, castling_rights):
                    return True
    return False


def causes_self_check(
    board,
    player_color: str,
    fr: int,
    fc: int,
    tr: int,
    tc: int,
    castling_rights: dict = None,
) -> bool:
    """Runs a dry-run array transformation on a deep copy to evaluate king vulnerabilities."""
    simulated_board = copy.deepcopy(board)

    # Execute speculative move
    piece = simulated_board[fr][fc]
    simulated_board[tr][tc] = piece
    simulated_board[fr][fc] = None

    king_pos = find_king(simulated_board, player_color)
    if not king_pos:
        return True  # Protect missing king fallbacks

    opponent_color = "black" if player_color == "white" else "white"
    return is_square_attacked(
        simulated_board, king_pos[0], king_pos[1], opponent_color, castling_rights
    )


def has_legal_moves(board, player_color: str, castling_rights: dict = None) -> bool:
    """Scans all player pieces for any geometric line that drops self-check vulnerability."""
    my_char_color = "w" if player_color == "white" else "b"
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece and piece.get("color") == my_char_color:
                for tr in range(8):
                    for tc in range(8):
                        if is_legal_move(board, r, c, tr, tc, castling_rights):
                            if not causes_self_check(
                                board, player_color, r, c, tr, tc, castling_rights
                            ):
                                return True  # At least one validation vector clears check escape pathing
    return False
