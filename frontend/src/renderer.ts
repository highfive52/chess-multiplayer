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
  const rows = viewer === "white" ? [...base].reverse() : base;
  const cols = viewer === "white" ? [...base].reverse() : base;

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
        const pieceElement = document.createElement("span");
        pieceElement.textContent = piece.type.toUpperCase();
        pieceElement.style.color = piece.color === "w" ? "#ffffff" : "#000000";

        if (piece.color === "w") {
          pieceElement.style.webkitTextStroke = "1px #1e1e1e";
        }

        square.appendChild(pieceElement);
      }

      boardContainer.appendChild(square);
    }
  }
}
