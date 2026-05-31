// frontend/src/renderer.ts
import type { BoardMatrix, Position } from "./types";

/**
 * Clears the chessboard container and programmatically paints the current matrix state.
 * Correctly renders Row 7 (Black Major Pieces) at the top and Row 0 (White Major Pieces) at the bottom.
 */
export function renderBoard(matrix: BoardMatrix, selectedPosition: Position | null = null): void {
  const boardContainer = document.getElementById("chess-board");
  if (!boardContainer) return;

  boardContainer.innerHTML = "";

  // 🔄 INVERT THE ROW LOOP: Start at 7 (Black) and decrement down to 0 (White)
  // This pushes White's baseline to the bottom row of the HTML layout grid organically!
  for (let row = 7; row >= 0; row--) {
    for (let col = 0; col < 8; col++) {
      const square = document.createElement("div");

      // Checkerboard math remains identical because addition is commutative
      const isLight = (row + col) % 2 === 0;
      square.className = `square ${isLight ? "light" : "dark"}`;

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
