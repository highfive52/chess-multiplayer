// frontend/src/main.ts
import { io } from "socket.io-client";
import { createInitialBoard } from "./boardState";
import { renderBoard } from "./renderer";
import type { Position, BoardMatrix } from "./types";
import { toAlgebraic } from "./coordinates";
import "./style.css";

console.log("TypeScript environment up and running!");

// --- GAME STATE CONTAINER ---
const board: BoardMatrix = createInitialBoard();
let selectedSquare: Position | null = null;
let myRole: "white" | "black" | "spectator" | null = null;

// Grab our dynamic HUD elements
const identityEl = document.getElementById("player-identity");
const turnEl = document.getElementById("turn-indicator");

// Initialize Network Socket Connection
const socket = io("http://localhost:8000");

// 🏁 TRIGGER 1: Synchronous Initial Draw on Application Boot
// renderBoard(board, selectedSquare);

// --- TRIGGER 2: REMOTE NETWORK INPUTS (SOCKET LISTENERS) ---
socket.on("connect", () => {
  console.log("Connected to the server successfully! Socket ID:", socket.id);

  // Explicitly request our identity over the stabilized WebSocket pipe
  socket.emit("request_role");
});

// Catch initial role assignment AND catch up to the current board state
socket.on(
  "assigned_role",
  (payload: {
    color: "white" | "black" | "spectator";
    board: BoardMatrix;
    current_turn: string;
  }) => {
    myRole = payload.color;

    // 1. Establish identity HUD element
    if (identityEl) {
      identityEl.textContent = myRole.toUpperCase();
      if (myRole === "white") identityEl.style.color = "#ffffff";
      if (myRole === "black") identityEl.style.color = "#000000";
      if (myRole === "spectator") identityEl.style.color = "#6b7280";
    }

    // 2. Hydrate the local board matrix with the server's current truth
    for (let r = 0; r < 8; r++) {
      board[r] = [...payload.board[r]];
    }

    // 3. Update the Turn HUD to reflect the active player
    if (turnEl) {
      const isMyTurn = myRole === payload.current_turn;
      if (myRole === "spectator") {
        turnEl.textContent = `Spectating - ${payload.current_turn.toUpperCase()}'s Turn`;
        turnEl.style.color = "#4b5563";
      } else if (isMyTurn) {
        turnEl.textContent = "YOUR TURN";
        turnEl.style.color = "#16a34a";
      } else {
        turnEl.textContent = "OPPONENT'S TURN";
        turnEl.style.color = "#dc2626";
      }
    }

    // 4. Force a fresh screen paint
    renderBoard(board, selectedSquare);
  }
);

// ONE AUTHORITATIVE SNAPSHOT LISTENER (Duplicates Cleaned Out)
socket.on(
  "move_executed",
  (payload: { board: BoardMatrix; current_turn: string; last_move: any }) => {
    console.log("📥 Authoritative state snapshot arrived from server!");

    // 1. Overwrite local memory array references entirely
    for (let r = 0; r < 8; r++) {
      board[r] = [...payload.board[r]];
    }

    // 2. Update Dynamic Turn HUD Indicator text and style
    if (turnEl) {
      const isMyTurn = myRole === payload.current_turn;

      if (myRole === "spectator") {
        turnEl.textContent = `Spectating - ${payload.current_turn.toUpperCase()}'s Turn`;
        turnEl.style.color = "#4b5563";
      } else if (isMyTurn) {
        turnEl.textContent = "YOUR TURN";
        turnEl.style.color = "#16a34a"; // Alert Green
      } else {
        turnEl.textContent = "OPPONENT'S TURN";
        turnEl.style.color = "#dc2626"; // Alert Red
      }
    }

    // 3. Repaint UI using master matrix layout
    renderBoard(board, selectedSquare);
  }
);

// --- TRIGGER 3: LOCAL HUMAN INPUT (CLICK INTERACTION LOOP) ---
const boardContainer = document.getElementById("chess-board");
if (boardContainer) {
  boardContainer.addEventListener("click", (event) => {
    const targetSquare = (event.target as HTMLElement).closest(".square") as HTMLElement;
    if (!targetSquare) return;

    const row = parseInt(targetSquare.dataset.row!, 10);
    const col = parseInt(targetSquare.dataset.col!, 10);
    const clickedPiece = board[row][col];

    console.log(`Clicked square: ${toAlgebraic(row, col)} | Indices: [${row}][${col}]`);

    // CASE 1: No piece is currently selected (Attempting to lift a piece)
    if (selectedSquare === null) {
      if (clickedPiece) {
        // 🔒 SAFETY CHECK: Map frontend character flags ("w"/"b") to identity role
        const pieceColorMapped = clickedPiece.color === "w" ? "white" : "black";

        if (myRole === "spectator") {
          console.log("Spectators cannot select or move pieces.");
          return;
        }

        if (pieceColorMapped !== myRole) {
          console.log(
            `Selection blocked. You are ${myRole?.toUpperCase()}, that piece is ${pieceColorMapped.toUpperCase()}`
          );
          return;
        }

        // Select the piece safely
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

      if (fromRow === row && fromCol === col) {
        selectedSquare = null;
        console.log("Deselected active piece.");
      } else {
        const movingPiece = board[fromRow][fromCol];

        if (movingPiece) {
          console.log(
            `🚀 Proposing move: ${
              movingPiece.color
            }${movingPiece.type.toUpperCase()} from ${toAlgebraic(
              fromRow,
              fromCol
            )} to ${toAlgebraic(row, col)}`
          );

          // Broadcast proposal up to server referee
          socket.emit("propose_move", {
            from: { row: fromRow, col: fromCol },
            to: { row, col },
          });
        }

        selectedSquare = null;
      }
    }

    renderBoard(board, selectedSquare);
  });
}
