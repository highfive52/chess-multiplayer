import type { Position } from "./types.ts";

const FILES = ["a", "b", "c", "d", "e", "f", "g", "h"];

/**
 * Translates matrix indices [row][col] to algebraic chess notation (e.g., [7][0] -> "a1")
 */
export function toAlgebraic(row: number, col: number): string {
  if (row < 0 || row > 7 || col < 0 || col > 7) {
    throw new Error(`Invalid matrix coordinates: [${row}][${col}]`);
  }
  const file = FILES[col];
  const rank = 8 - row; // Row 0 is Rank 8, Row 7 is Rank 1
  return `${file}${rank}`;
}

/**
 * Translates algebraic notation back to matrix indices (e.g., "a1" -> { row: 7, col: 0 })
 */
export function toMatrix(algebraic: string): Position {
  if (algebraic.length !== 2) {
    throw new Error(`Invalid algebraic notation format: ${algebraic}`);
  }
  const file = algebraic[0].toLowerCase();
  const rank = parseInt(algebraic[1], 10);

  const col = FILES.indexOf(file);
  const row = 8 - rank;

  if (col === -1 || row < 0 || row > 7) {
    throw new Error(`Out of bounds algebraic coordinate: ${algebraic}`);
  }

  return { row, col };
}
