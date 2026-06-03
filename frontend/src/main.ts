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
let currentMatchStatus: "active" | "completed" = "active";

// Grab our structural screens
const lobbyScreen = document.getElementById("lobby-screen");
const appContainer = document.getElementById("app-container");

// Grab our dynamic HUD elements
const identityEl = document.getElementById("player-identity");
const turnEl = document.getElementById("turn-indicator");
const roomDisplay = document.getElementById("room-display");

// Grab lobby control elements
const btnCreate = document.getElementById("btn-create") as HTMLButtonElement;
const btnJoin = document.getElementById("btn-join") as HTMLButtonElement;
const inputRoomCode = document.getElementById("input-room-code") as HTMLInputElement;

// Initialize Network Socket Connection
const BACKEND_URL =
  window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://localhost:8000"
    : "https://chess-multiplayer-k792.onrender.com";

// Check if an ID already exists in the browser's storage
let userId = localStorage.getItem("chess_user_id");

if (!userId) {
  userId = crypto.randomUUID();
  localStorage.setItem("chess_user_id", userId);
  console.log(`[IDENTITY] Fresh token generated & saved: ${userId}`);
} else {
  console.log(`[IDENTITY] Welcome back. Existing token loaded: ${userId}`);
}

const socket = io(BACKEND_URL, {
  transports: ["websocket", "polling"],
  auth: {
    userId,
  },
});

// 🏁 TRIGGER 1: Synchronous Initial Draw & Auto-Join URL Parsing
renderBoard(board, selectedSquare, myRole);

// Check if a room code is already embedded in the browser's address bar
const urlParams = new URLSearchParams(window.location.search);
const roomFromUrl = urlParams.get("room")?.trim().toUpperCase();

if (roomFromUrl && roomFromUrl.length === 4) {
  console.log(`[BOOT] Detected room parameter in URL. Auto-joining: ${roomFromUrl}`);
  if (inputRoomCode) inputRoomCode.value = roomFromUrl;
  socket.emit("join_room", { roomId: roomFromUrl });
}

// --- TRIGGER 2: REMOTE NETWORK INPUTS (SOCKET LISTENERS) ---
const loaderEl = document.getElementById("server-loader");

socket.on("connect", () => {
  console.log(`⚡ Connected to backend at ${BACKEND_URL}! ID:`, socket.id);

  const hideLoader = () => {
    const activeLoader = document.getElementById("server-loader");
    if (activeLoader) {
      activeLoader.style.opacity = "0";
      setTimeout(() => {
        activeLoader.style.display = "none";
      }, 500);
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", hideLoader);
  } else {
    hideLoader();
  }
});

socket.on("disconnect", () => {
  console.warn("❌ Disconnected from cloud server.");
  if (loaderEl) {
    loaderEl.style.display = "flex";
    loaderEl.style.opacity = "1";
  }
});

// --- LOBBY CORE INTERACTION RULES ---

if (btnCreate) {
  btnCreate.addEventListener("click", () => {
    const characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    let randomCode = "";
    for (let i = 0; i < 4; i++) {
      randomCode += characters.charAt(Math.floor(Math.random() * characters.length));
    }
    console.log(`[LOBBY] Requesting creation of Room: ${randomCode}`);

    const currentUrl = new URL(window.location.href);
    currentUrl.searchParams.set("room", randomCode);
    window.history.pushState({ path: currentUrl.toString() }, "", currentUrl.toString());

    socket.emit("join_room", { roomId: randomCode });
  });
}

if (btnJoin && inputRoomCode) {
  btnJoin.addEventListener("click", () => {
    const enteredCode = inputRoomCode.value.trim().toUpperCase();
    if (enteredCode.length !== 4) {
      alert("Please enter a valid 4-character room code.");
      return;
    }
    console.log(`[LOBBY] Requesting entry to Room: ${enteredCode}`);

    const currentUrl = new URL(window.location.href);
    currentUrl.searchParams.set("room", enteredCode);
    window.history.pushState({ path: currentUrl.toString() }, "", currentUrl.toString());

    socket.emit("join_room", { roomId: enteredCode });
  });
}

// Catch initial role assignment AND catch up to the current board state
socket.on(
  "assigned_role",
  (payload: {
    room_id: string;
    color: "white" | "black" | "spectator";
    board: BoardMatrix;
    current_turn: string;
    status: "active" | "completed"; // ◄ NEW FIELD
    winner: string | null; // ◄ NEW FIELD
    check_status: "white" | "black" | null; // ◄ NEW FIELD
  }) => {
    myRole = payload.color;
    currentMatchStatus = payload.status; // ◄ Capture initial or historical match state

    // 1. Establish room code and identity HUD elements
    if (roomDisplay) {
      roomDisplay.textContent = payload.room_id;
    }

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

    // 3. Update the Turn HUD to reflect the active player or historical game-over
    if (turnEl) {
      if (payload.status === "completed") {
        turnEl.textContent = payload.winner
          ? `CHECKMATE - ${payload.winner.toUpperCase()} WINS! 🎉`
          : "GAME OVER - DRAW";
        turnEl.style.color = "#a855f7";
      } else {
        const isMyTurn = myRole === payload.current_turn;
        const checkSuffix = payload.check_status === payload.current_turn ? " (IN CHECK)" : "";

        if (myRole === "spectator") {
          turnEl.textContent = `Spectating - ${payload.current_turn.toUpperCase()}'s Turn${checkSuffix}`;
          turnEl.style.color = "#4b5563";
        } else if (isMyTurn) {
          turnEl.textContent = `YOUR TURN${checkSuffix}`;
          turnEl.style.color = payload.check_status ? "#ea580c" : "#16a34a";
        } else {
          turnEl.textContent = `OPPONENT'S TURN${checkSuffix}`;
          turnEl.style.color = "#dc2626";
        }
      }
    }

    // Transition views from Lobby to Active Game Room
    if (lobbyScreen) lobbyScreen.classList.add("hidden");
    if (appContainer) appContainer.classList.remove("hidden");

    // 4. Force a fresh screen paint (pass viewer role so board orients correctly)
    renderBoard(board, selectedSquare, myRole);
  }
);

// AUTHORITATIVE SNAPSHOT LISTENER WITH RULE ENFORCEMENT
socket.on(
  "move_executed",
  (payload: {
    board: BoardMatrix;
    current_turn: string;
    status: "active" | "completed";
    winner: string | null;
    check_status: "white" | "black" | null;
    last_move: { from: { row: number; col: number }; to: { row: number; col: number } } | null;
  }) => {
    console.log("📥 Authoritative state snapshot arrived from server!");
    currentMatchStatus = payload.status;

    // 1. Overwrite local memory array references entirely
    for (let r = 0; r < 8; r++) {
      board[r] = [...payload.board[r]];
    }

    // 2. Handle Game Status & Turn HUD Indicator text and style
    if (turnEl) {
      if (payload.status === "completed") {
        const winMessage = payload.winner
          ? `CHECKMATE - ${payload.winner.toUpperCase()} WINS! 🎉`
          : "GAME OVER - DRAW";

        turnEl.textContent = winMessage;
        turnEl.style.color = "#a855f7"; // Elegant Victory Purple

        setTimeout(() => alert(winMessage), 50);
      } else {
        const isMyTurn = myRole === payload.current_turn;
        const checkSuffix = payload.check_status === payload.current_turn ? " (IN CHECK)" : "";

        if (myRole === "spectator") {
          turnEl.textContent = `Spectating - ${payload.current_turn.toUpperCase()}'s Turn${checkSuffix}`;
          turnEl.style.color = "#4b5563";
        } else if (isMyTurn) {
          turnEl.textContent = `YOUR TURN${checkSuffix}`;
          turnEl.style.color = payload.check_status ? "#ea580c" : "#16a34a";
        } else {
          turnEl.textContent = `OPPONENT'S TURN${checkSuffix}`;
          turnEl.style.color = "#dc2626";
        }
      }
    }

    // 3. Reset local click selections cleanly if the game is over to freeze interactions
    if (payload.status === "completed") {
      selectedSquare = null; // Set to type safe null instead of invalid index markers
    }

    // 4. Repaint UI using master matrix layout (preserve viewer orientation)
    renderBoard(board, selectedSquare, myRole);
  }
);

// --- TRIGGER 3: LOCAL HUMAN INPUT (CLICK INTERACTION LOOP) ---
const boardContainer = document.getElementById("chess-board");
if (boardContainer) {
  boardContainer.addEventListener("click", (event) => {
    // 🛑 FREEZE INTERACTION GUARD
    if (currentMatchStatus === "completed") {
      console.log("[BOARD FROZEN] Click ignored. Match has concluded via checkmate.");
      return;
    }
    const targetSquare = (event.target as HTMLElement).closest(".square") as HTMLElement;
    if (!targetSquare) return;

    const row = parseInt(targetSquare.dataset.row!, 10);
    const col = parseInt(targetSquare.dataset.col!, 10);
    const clickedPiece = board[row][col];

    console.log(`Clicked square: ${toAlgebraic(row, col)} | Indices: [${row}][${col}]`);

    // CASE 1: No piece is currently selected (Attempting to lift a piece)
    if (selectedSquare === null) {
      if (clickedPiece) {
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

          socket.emit("propose_move", {
            from: { row: fromRow, col: fromCol },
            to: { row, col },
          });
        }

        selectedSquare = null;
      }
    }

    renderBoard(board, selectedSquare, myRole);
  });
}
