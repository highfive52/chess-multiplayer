// frontend/src/main.ts
import { io } from "socket.io-client";
import { createInitialBoard } from "./boardState";
import { renderBoard } from "./renderer";
import type { Position, BoardMatrix } from "./types";
import { toAlgebraic } from "./coordinates";

console.log("TypeScript environment up and running!");

// --- GAME STATE CONTAINER ---
const board: BoardMatrix = createInitialBoard();
let selectedSquare: Position | null = null;

// Initialize Network Socket Connection
const socket = io("http://localhost:8000");

// 🏁 TRIGGER 1: Synchronous Initial Draw on Application Boot
renderBoard(board, selectedSquare);

// --- TRIGGER 2: REMOTE NETWORK INPUTS (SOCKET LISTENERS) ---
socket.on("connect", () => {
  console.log("Connected to the server successfully! Socket ID:", socket.id);
});

// Listen for incoming opponent moves from the server backend
socket.on("move", (payload: { from: Position; to: Position }) => {
  const { from, to } = payload;

  console.log(
    `📡 Network move received: From [${from.row}][${from.col}] to [${to.row}][${to.col}]`
  );

  // Target the item currently resting at the incoming address coordinates
  const movingPiece = board[from.row][from.col];

  if (movingPiece) {
    // Replicate the movement data mutation in our local matrix memory array
    board[to.row][to.col] = movingPiece;
    board[from.row][from.col] = null;

    // Repaint the screen so the player sees the opponent's pieces move automatically
    renderBoard(board, selectedSquare);
  }
});

// --- TRIGGER 3: LOCAL HUMAN INPUT (CLICK INTERACTION LOOP) ---
const boardContainer = document.getElementById("chess-board");
if (boardContainer) {
  boardContainer.addEventListener("click", (event) => {
    // Find the closest parent div with the class "square"
    const targetSquare = (event.target as HTMLElement).closest(".square") as HTMLElement;
    if (!targetSquare) return;

    // Extract the row/col coordinates from the HTML data attributes
    const row = parseInt(targetSquare.dataset.row!, 10);
    const col = parseInt(targetSquare.dataset.col!, 10);
    const clickedPiece = board[row][col];

    console.log(`Clicked square: ${toAlgebraic(row, col)} | Indices: [${row}][${col}]`);

    // CASE 1: No piece is currently selected
    if (selectedSquare === null) {
      if (clickedPiece) {
        // Select the piece
        selectedSquare = { row, col };
        console.log(`Selected piece: ${clickedPiece.color}${clickedPiece.type.toUpperCase()}`);
      } else {
        console.log("Empty square clicked. Nothing to select.");
      }
    }
    // CASE 2: A piece was already selected, meaning this click is a destination target
    else {
      const fromRow = selectedSquare.row;
      const fromCol = selectedSquare.col;

      // If they clicked the exact same square twice, just deselect it
      if (fromRow === row && fromCol === col) {
        selectedSquare = null;
        console.log("Deselected active piece.");
      } else {
        // Execute the move local memory state mutation
        const movingPiece = board[fromRow][fromCol];

        if (movingPiece) {
          console.log(
            `Moving ${movingPiece.color}${movingPiece.type.toUpperCase()} from ${toAlgebraic(
              fromRow,
              fromCol
            )} to ${toAlgebraic(row, col)}`
          );

          // Move the piece reference to the target index address
          board[row][col] = movingPiece;
          // Clear the old home square index address
          board[fromRow][fromCol] = null;

          // Broadcast this move payload over the network
          socket.emit("move", {
            from: { row: fromRow, col: fromCol },
            to: { row, col },
          });
        } // <--- Fixed: This brace now safely closes if (movingPiece)

        // Reset tracking state after a completed move interaction
        selectedSquare = null;
      }
    }

    // Redraw the visual board layer to reflect local state mutations
    renderBoard(board, selectedSquare);
  });
}
