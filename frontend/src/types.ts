export type PieceType = "p" | "r" | "n" | "b" | "q" | "k";
export type PieceColor = "w" | "b";

export interface Piece {
  id: string; // Unique identifier (e.g., 'w-p-0' for white pawn 0)
  type: PieceType; // p=Pawn, r=Rook, n=Knight, b=Bishop, q=Queen, k=King
  color: PieceColor; // w=White, b=Black
}

// A Square can hold a Piece or be empty (null)
export type BoardMatrix = (Piece | null)[][];

export interface Position {
  row: number; // 0 to 7
  col: number; // 0 to 7
}
