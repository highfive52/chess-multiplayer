import type { BoardMatrix, Position } from "./types";

/**
 * Clears the chessboard container and programmatically paints the current matrix state.
 */
export function renderBoard(matrix: BoardMatrix, selectedPosition: Position | null = null): void {
  const boardContainer = document.getElementById("chess-board");
  if (!boardContainer) return;

  // Clear out old elements to prevent appending duplicate boards on re-renders
  boardContainer.innerHTML = "";

  for (let row = 0; row < 8; row++) {
    for (let col = 0; col < 8; col++) {
      const square = document.createElement("div");

      // Checkerboard math: if row + col is an even number, it's a light square!
      // Examples: Top-left [0][0] = 0 (light). Next over [0][1] = 1 (dark).
      const isLight = (row + col) % 2 === 0;
      square.className = `square ${isLight ? "light" : "dark"}`;

      // Attach HTML5 data attributes so we can instantly look up indices on click events
      square.dataset.row = row.toString();
      square.dataset.col = col.toString();

      // Check if this specific square is currently selected
      if (selectedPosition && selectedPosition.row === row && selectedPosition.col === col) {
        square.classList.add("selected");
      }

      // Look into our data matrix to see if a piece is sitting at this index
      const piece = matrix[row][col];
      if (piece) {
        const pieceElement = document.createElement("span");
        pieceElement.textContent = piece.type.toUpperCase();
        pieceElement.style.color = piece.color === "w" ? "#ffffff" : "#000000";

        // Add a clean border stroke around white text so it's visible on light squares
        if (piece.color === "w") {
          pieceElement.style.webkitTextStroke = "1px #1e1e1e";
        }

        square.appendChild(pieceElement);
      }

      boardContainer.appendChild(square);
    }
  }
}
