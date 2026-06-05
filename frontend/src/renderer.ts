// frontend/src/renderer.ts
import type { BoardMatrix, Position } from "./types";

/**
 * Clears the chessboard container and programmatically paints the current matrix state.
 */
export function renderBoard(
  matrix: BoardMatrix,
  selectedPosition: Position | null = null,
  // viewer: 'white' | 'black' | 'spectator' — defaults to white view
  viewer: "white" | "black" | "spectator" | null = "white"
): void {
  const boardContainer = document.getElementById("chess-board");
  if (!boardContainer) return;

  boardContainer.innerHTML = "";

  // Determine rendering order based on viewer orientation.
  // - For a white viewer we render logical rows 0..7 and cols 0..7 so
  //   white (matrix[7]) appears at the bottom and white pieces move "up".
  // - For a black viewer we render rows 7..0 and cols 7..0 to rotate
  //   the board 180 degrees so black pieces appear at the bottom and
  //   also move "up" from the black player's perspective.
  const base = Array.from({ length: 8 }, (_, i) => i);
  const rows = viewer === "black" ? [...base].reverse() : base;
  const cols = base;

  for (const row of rows) {
    for (const col of cols) {
      const square = document.createElement("div");

      // Checkerboard math remains identical because addition is commutative
      const isLight = (row + col) % 2 === 0;
      square.className = `square ${isLight ? "light" : "dark"}`;

      // Store logical coordinates so click handlers map back to matrix indices
      square.dataset.row = row.toString();
      square.dataset.col = col.toString();

      if (selectedPosition && selectedPosition.row === row && selectedPosition.col === col) {
        square.classList.add("selected");
      }

      const piece = matrix[row][col];
      if (piece) {
        // Use SVG assets from the public folder so graphics are crisp on all displays.
        const pieceImg = document.createElement("img");
        pieceImg.src = `${import.meta.env.BASE_URL}pieces/${piece.color}-${piece.type}.svg`;
        pieceImg.alt = `${piece.color === "w" ? "White" : "Black"} ${piece.type.toUpperCase()}`;
        pieceImg.className = "chess-piece";
        pieceImg.setAttribute("draggable", "false");

        // Helpful data attributes for pointer handling and debugging
        pieceImg.dataset.row = row.toString();
        pieceImg.dataset.col = col.toString();
        if ("id" in piece && piece.id != null) pieceImg.dataset.pieceId = String(piece.id);

        square.appendChild(pieceImg);
      }

      boardContainer.appendChild(square);
    }
  }
}
