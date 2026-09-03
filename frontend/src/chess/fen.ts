import type { BoardMatrix, Piece, PieceType } from "../types";

export interface ParsedFen {
  board: BoardMatrix;
  activeColor: "w" | "b";
  castling: string;
  enPassant: string | null;
  halfmoveClock: number;
  fullmoveNumber: number;
}

const PIECE_MAP: Record<string, { type: PieceType; color: "w" | "b" }> = {
  p: { type: "p", color: "b" },
  r: { type: "r", color: "b" },
  n: { type: "n", color: "b" },
  b: { type: "b", color: "b" },
  q: { type: "q", color: "b" },
  k: { type: "k", color: "b" },
  P: { type: "p", color: "w" },
  R: { type: "r", color: "w" },
  N: { type: "n", color: "w" },
  B: { type: "b", color: "w" },
  Q: { type: "q", color: "w" },
  K: { type: "k", color: "w" },
};

/**
 * Parse a FEN string into a BoardMatrix and metadata.
 * The returned `board` uses the same logical row ordering as the app
 * (row 0 = Black back rank, row 7 = White back rank).
 */
export function parseFen(fen: string): ParsedFen {
  if (fen == null) throw new Error("invalid FEN: empty");

  // Treat empty string as the starting position (robustness for legacy rows)
  if (typeof fen === "string" && fen.trim() === "") {
    fen = "startpos";
  }

  // Support the special 'startpos' token used by the backend to mean the
  // standard chess starting position.
  // Trim surrounding whitespace and defensive-strip outer quotes that may
  // appear if the value was double-encoded or stored with quotes.
  if (typeof fen === "string") {
    fen = fen.trim();
    // strip matching outer quotes
    if ((fen.startsWith('"') && fen.endsWith('"')) || (fen.startsWith("'") && fen.endsWith("'"))) {
      fen = fen.slice(1, -1).trim();
    }
  }

  if (fen === "startpos") {
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
  }

  const parts = fen.trim().split(" ");
  if (parts.length < 1) throw new Error("invalid FEN: empty");

  const placement = parts[0];
  let rows = placement.split("/");
  if (rows.length !== 8) {
    // Be tolerant of malformed or legacy persisted values; fall back to startpos
    // and avoid throwing which breaks the replay UI entirely.
    console.warn("Malformed FEN placement; falling back to start position:", fen);
    fen = "startpos";
    const _parts = fen.trim().split(" ");
    // replace parts/placement/rows with startpos values
    // (we know startpos expands to a correct 8-rank FEN above)
    const placement2 = _parts[0];
    const rows2 = placement2.split("/");
    // overwrite rows for downstream parsing
    rows = rows2;
  }

  // initialize empty 8x8 board (null = empty)
  const board: BoardMatrix = Array.from({ length: 8 }, () => Array(8).fill(null));

  for (let r = 0; r < 8; r++) {
    const rank = rows[r]; // FEN ranks go from 8 (index 0) to 1 (index 7)
    let c = 0;
    for (const ch of rank) {
      if (c >= 8) break;
      if (ch >= "1" && ch <= "8") {
        const empty = parseInt(ch, 10);
        c += empty;
        continue;
      }
      const mapping = PIECE_MAP[ch];
      if (!mapping) throw new Error(`invalid FEN piece char: ${ch}`);
      const piece: Piece = {
        id: `${mapping.color}-${mapping.type}-${r}-${c}`,
        type: mapping.type,
        color: mapping.color,
      };
      board[r][c] = piece;
      c += 1;
    }
    if (c !== 8) {
      // allow short rows only if they total 8 via digits; otherwise invalid
      throw new Error(`invalid FEN rank '${rank}' did not sum to 8 squares`);
    }
  }

  const activeColor = (parts[1] || "w") as "w" | "b";
  const castling = parts[2] || "";
  const enPassant = parts[3] && parts[3] !== "-" ? parts[3] : null;
  const halfmoveClock = parts[4] ? parseInt(parts[4], 10) : 0;
  const fullmoveNumber = parts[5] ? parseInt(parts[5], 10) : 1;

  return {
    board,
    activeColor,
    castling,
    enPassant,
    halfmoveClock,
    fullmoveNumber,
  };
}

/** Convenience: convert FEN into just the BoardMatrix */
export function fenToBoard(fen: string): BoardMatrix {
  return parseFen(fen).board;
}

export default {
  parseFen,
  fenToBoard,
};
