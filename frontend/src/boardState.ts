import type { BoardMatrix, PieceType } from "./types.ts";

// Standard home row order from left to right (a to h)
const BACK_ROW_SETUP: PieceType[] = ["r", "n", "b", "q", "k", "b", "n", "r"];

export function createInitialBoard(): BoardMatrix {
  // Initialize a blank 8x8 matrix filled with null
  const board: BoardMatrix = Array(8)
    .fill(null)
    .map(() => Array(8).fill(null));

  // 1. Populate Black Pieces (Row 0 = Back Row, Row 1 = Pawns)
  board[0] = BACK_ROW_SETUP.map((type, col) => ({
    id: `b-${type}-${col}`,
    type,
    color: "b",
  }));
  board[1] = Array(8)
    .fill(null)
    .map((_, col) => ({
      id: `b-p-${col}`,
      type: "p",
      color: "b",
    }));

  // 2. Populate White Pieces (Row 6 = Pawns, Row 7 = Back Row)
  board[6] = Array(8)
    .fill(null)
    .map((_, col) => ({
      id: `w-p-${col}`,
      type: "p",
      color: "w",
    }));
  board[7] = BACK_ROW_SETUP.map((type, col) => ({
    id: `w-${type}-${col}`,
    type,
    color: "w",
  }));

  return board;
}
