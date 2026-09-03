// frontend/src/main.ts
import { io } from "socket.io-client";
import { createInitialBoard } from "./boardState";
import { renderBoard } from "./renderer";
import type { Position, BoardMatrix } from "./types";
import "./style.css";
import ReplayController from "./replay";

console.log("TypeScript environment up and running!");

// Helpers: coordinate formatting for logs (matrix coords -> algebraic e.g. D2)
function toAlgebraic(row: number, col: number): string {
  const file = String.fromCharCode(65 + col); // A-H
  const rank = 8 - row; // matrix row 0 -> rank 8
  return `${file}${rank}`;
}

function fmtCoord(row: number, col: number): string {
  return `${row},${col} (${toAlgebraic(row, col)})`;
}

// --- GAME STATE CONTAINER ---
const board: BoardMatrix = createInitialBoard();
let selectedSquare: Position | null = null;
let myRole: "white" | "black" | "spectator" | null = null;
let currentMatchStatus: "active" | "completed" = "active";
let currentTurn: string = "white";
// When true, suppress live-room creation and all outbound move events.
let isReplayMode = false;

// --- USER PREFERENCES ---
type InputMode = "drag" | "click" | "hybrid";
let inputPreference: InputMode =
  (localStorage.getItem("chess_input_mode") as InputMode) || "hybrid";

// Grab structural screens & HUD references
const serverLoader = document.getElementById("server-loader");
const lobbyScreen = document.getElementById("lobby-screen");
const appContainer = document.getElementById("app-container");
const identityEl = document.getElementById("player-identity");
const turnEl = document.getElementById("turn-indicator");
const roomDisplay = document.getElementById("room-display");

// Grab settings elements
const settingsModal = document.getElementById("settings-modal");
const btnSettings = document.getElementById("btn-settings");
const btnCloseSettings = document.getElementById("btn-close-settings");
const selectInputMode = document.getElementById("select-input-mode") as HTMLSelectElement;

// --- NETWORK INITIALIZATION ---
const BACKEND_URL =
  window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://localhost:8000"
    : "https://chess-multiplayer-k792.onrender.com";

let userId = localStorage.getItem("chess_user_id");
if (!userId) {
  userId = crypto.randomUUID();
  localStorage.setItem("chess_user_id", userId);
}

const socket = io(BACKEND_URL, {
  transports: ["websocket", "polling"],
  auth: { userId },
});

// DOM refs for connection UI
const btnRetry = document.getElementById("btn-retry") as HTMLButtonElement | null;
const btnCopyLink = document.getElementById("btn-copy-link") as HTMLButtonElement | null;
const connStatus = document.getElementById("conn-status") as HTMLElement | null;
const btnCreateEl = () => document.getElementById("btn-create") as HTMLButtonElement | null;
const btnJoinEl = () => document.getElementById("btn-join") as HTMLButtonElement | null;

// Toast utilities
function showToast(msg: string, ms = 1800) {
  let root = document.getElementById("toast-root");
  if (!root) {
    root = document.createElement("div");
    root.id = "toast-root";
    document.body.appendChild(root);
  }
  const t = document.createElement("div");
  t.className = "toast";
  t.textContent = msg;
  root.appendChild(t);
  setTimeout(() => {
    t.remove();
  }, ms);
}

// --- SCREEN VIEW ROUTING CONTROLLERS ---
function setRetryVisible(visible: boolean) {
  if (!btnRetry) return;
  btnRetry.style.display = visible ? "inline-block" : "none";
}
function showLobby() {
  if (serverLoader) serverLoader.classList.add("hidden");
  if (appContainer) appContainer.classList.add("hidden");
  if (lobbyScreen) lobbyScreen.classList.remove("hidden");
  updateOpenReplayVisibility(false);
}

function showGameRoom() {
  if (serverLoader) serverLoader.classList.add("hidden");
  if (lobbyScreen) lobbyScreen.classList.add("hidden");
  if (appContainer) appContainer.classList.remove("hidden");
  updateOpenReplayVisibility(true);
}

// Hide the bottom-page "Open Replay" while inside an active game; show it on the lobby
function updateOpenReplayVisibility(inGame: boolean) {
  const btn = document.getElementById("btn-open-replay");
  if (!btn) return;
  btn.style.display = inGame ? "none" : "inline-block";
}

// --- SAFE DOM EVENT LIFECYCLE WRAPPER ---
document.addEventListener("DOMContentLoaded", () => {
  // Grab Lobby Action Buttons safely on ready state
  const btnCreate = document.getElementById("btn-create") as HTMLButtonElement;
  const btnJoin = document.getElementById("btn-join") as HTMLButtonElement;
  const btnOpenReplayLobby = document.getElementById("btn-open-replay-lobby");
  const inputRoomCode = document.getElementById("input-room-code") as HTMLInputElement;

  // Initialize Modal Dropdown Values on Bootup
  if (selectInputMode) {
    selectInputMode.value = inputPreference;
  }

  // Bind Modal Visibility Listeners
  if (btnSettings && settingsModal) {
    btnSettings.addEventListener("click", () => settingsModal.classList.remove("hidden"));
  }
  if (btnCloseSettings && settingsModal) {
    btnCloseSettings.addEventListener("click", () => settingsModal.classList.add("hidden"));
  }
  if (settingsModal) {
    settingsModal.addEventListener("click", (e) => {
      if (e.target === settingsModal) settingsModal.classList.add("hidden");
    });
  }

  // Bind Dropdown Selector Changes
  if (selectInputMode) {
    selectInputMode.addEventListener("change", (e) => {
      const target = e.target as HTMLSelectElement;
      inputPreference = target.value as InputMode;
      localStorage.setItem("chess_input_mode", inputPreference);

      selectedSquare = null;
      renderBoard(board, selectedSquare, myRole);
    });
  }

  // --- BIND BUTTON UI HANDLERS FOR LOBBY TRANSACTIONS ---
  if (btnCreate) {
    btnCreate.addEventListener("click", () => {
      if (isReplayMode) {
        showToast("Exit replay mode before creating a game");
        return;
      }
      if (!socket.connected) {
        alert("Not connected to backend. Trying to reconnect...");
        try {
          socket.connect();
        } catch (e) {
          console.debug(e);
        }
        return;
      }
      socket.emit("create_room");
    });
  }

  if (btnJoin && inputRoomCode) {
    btnJoin.addEventListener("click", () => {
      if (isReplayMode) {
        showToast("Exit replay mode before joining a game");
        return;
      }
      const code = inputRoomCode.value.trim().toUpperCase();
      if (code.length === 4) {
        socket.emit("join_room", { roomId: code });
      } else {
        alert("Please enter a valid 4-letter room code.");
      }
    });
  }

  // Show lobby immediately so buttons are usable while socket connects
  showLobby();

  // Wire retry and copy-link if present
  if (btnRetry) {
    btnRetry.addEventListener("click", () => {
      if (socket.connected) {
        showToast("Already connected");
        return;
      }
      showToast("Reconnecting...");
      try {
        socket.connect();
      } catch (e) {
        console.warn(e);
      }
    });
    // initial visibility based on current socket state
    setRetryVisible(!socket.connected);
  }

  if (btnCopyLink) {
    btnCopyLink.addEventListener("click", async () => {
      const url = window.location.href;
      try {
        await navigator.clipboard.writeText(url);
        showToast("Link copied to clipboard");
      } catch {
        showToast("Unable to copy link");
      }
    });
  }

  // --- Replay Controls wiring ---
  const btnOpenReplay = document.getElementById("btn-open-replay");
  const replayControls = document.getElementById("replay-controls");
  const btnFirst = document.getElementById("btn-first");
  const btnPrev = document.getElementById("btn-prev");
  const btnNext = document.getElementById("btn-next");
  const btnLast = document.getElementById("btn-last");
  const btnPlay = document.getElementById("btn-play");
  const selectSpeed = document.getElementById("select-speed") as HTMLSelectElement | null;
  const btnJump = document.getElementById("btn-jump");
  const inputJump = document.getElementById("replay-jump") as HTMLInputElement | null;
  const replayStatus = document.getElementById("replay-status");
  const btnExitReplay = document.getElementById("btn-exit-replay");

  const replay = new ReplayController(BACKEND_URL);

  function updateReplayView() {
    const boardMatrix = replay.getCurrentBoard();
    // If replay returns null (invalid/missing FEN), render a vanilla initial board
    // so First/Previous/Jump-to-0 always show the starting position.
    const toRender = boardMatrix ?? createInitialBoard();
    renderBoard(toRender, null, "white");
    if (replayStatus) {
      const left = replay.getDisplayPly();
      const right = replay.getMaxPly();
      replayStatus.textContent = `${left} / ${right}`;
      // UI status updated
    }
    // update move history highlighting
    renderMoveHistory();
  }

  // Replay modal elements (non-blocking)
  const replayModal = document.getElementById("replay-modal");
  const replayModalInput = document.getElementById("replay-game-id") as HTMLInputElement | null;
  const btnLoadReplay = document.getElementById("btn-load-replay");
  const replayError = document.getElementById("replay-error");
  const btnCloseReplayModal = document.getElementById("btn-close-replay-modal");
  const replayList = document.getElementById("replay-list");

  if (btnOpenReplay) {
    btnOpenReplay.addEventListener("click", () => {
      if (replayModal) replayModal.classList.remove("hidden");
      if (replayModalInput) replayModalInput.focus();
      // load available games into the modal
      loadAvailableGames();
    });
  }

  if (btnOpenReplayLobby) {
    btnOpenReplayLobby.addEventListener("click", () => {
      if (replayModal) replayModal.classList.remove("hidden");
      if (replayModalInput) replayModalInput.focus();
      // load available games into the modal
      loadAvailableGames();
    });
  }

  if (btnCloseReplayModal && replayModal) {
    btnCloseReplayModal.addEventListener("click", () => replayModal.classList.add("hidden"));
  }

  if (btnLoadReplay && replayModalInput) {
    btnLoadReplay.addEventListener("click", async () => {
      const gid = replayModalInput.value.trim();
      if (!gid) return;
      try {
        await replay.load(gid);
        updateReplayView();
        // If the loaded replay doesn't provide a valid board FEN, show an inline error
        const boardMatrix = replay.getCurrentBoard();
        if (!boardMatrix) {
          const msg = "Replay loaded but starting position is unavailable.";
          if (replayError) {
            replayError.textContent = msg;
            replayError.classList.remove("hidden");
          } else {
            alert(msg);
          }
          return;
        }
        if (replayControls) replayControls.classList.remove("hidden");
        // Enter replay mode: disable live-room interactions and local piece movement
        isReplayMode = true;
        // show the game view so the board and controls are visible while replaying
        showGameRoom();
        // show move history panel and render list
        const mh = document.getElementById("move-history");
        if (mh) mh.classList.remove("hidden");
        renderMoveHistory();
        // hide modal after successful load
        if (replayModal) replayModal.classList.add("hidden");
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        if (replayError) {
          replayError.textContent = msg;
          replayError.classList.remove("hidden");
        } else {
          alert(`Failed to load replay: ${msg}`);
        }
      }
    });
  }

  async function loadAvailableGames() {
    if (!replayList) return;
    replayList.innerHTML = "Loading...";
    try {
      const resp = await fetch(`${BACKEND_URL}/games?status=active`);
      if (!resp.ok) throw new Error(`status=${resp.status}`);
      const docs = (await resp.json()) as Array<{ id: string; room_code?: string }>;
      if (!Array.isArray(docs) || docs.length === 0) {
        replayList.innerHTML = '<div class="note">No active games found.</div>';
        return;
      }
      replayList.innerHTML = "";
      docs.forEach((g) => {
        const btn = document.createElement("button");
        btn.className = "btn-small";
        btn.style.display = "block";
        btn.style.width = "100%";
        btn.style.marginBottom = "6px";
        btn.textContent = `${g.room_code ?? "----"} — ${g.id}`;
        btn.addEventListener("click", async () => {
          try {
            await replay.load(g.id);
            updateReplayView();
            const boardMatrix = replay.getCurrentBoard();
            if (!boardMatrix) {
              const msg = "Replay loaded but starting position is unavailable.";
              if (replayError) {
                replayError.textContent = msg;
                replayError.classList.remove("hidden");
              } else {
                alert(msg);
              }
              return;
            }
            if (replayControls) replayControls.classList.remove("hidden");
            // Enter replay mode: disable live-room interactions and local piece movement
            isReplayMode = true;
            // show the game view so the board and controls are visible while replaying
            showGameRoom();
            // show move history panel and render list
            const mh = document.getElementById("move-history");
            if (mh) mh.classList.remove("hidden");
            renderMoveHistory();
            if (replayModal) replayModal.classList.add("hidden");
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            if (replayError) {
              replayError.textContent = msg;
              replayError.classList.remove("hidden");
            } else {
              alert(msg);
            }
          }
        });
        replayList.appendChild(btn);
      });
    } catch (err: unknown) {
      replayList.innerHTML = "";
      const msg = err instanceof Error ? err.message : String(err);
      if (replayError) {
        replayError.textContent = msg;
        replayError.classList.remove("hidden");
      } else {
        replayList.textContent = `Error: ${msg}`;
      }
    }
  }

  // --- Move history rendering & interactions ---
  function renderMoveHistory() {
    const container = document.getElementById("move-list");
    const mh = document.getElementById("move-history");
    if (!container || !replay.doc) return;
    container.innerHTML = "";
    const moves = replay.doc.moves;
    moves.forEach((m, idx) => {
      const item = document.createElement("div");
      item.className = "move-item";
      if (idx === replay.currentPly) item.classList.add("current");

      const plyEl = document.createElement("div");
      plyEl.className = "ply";
      plyEl.textContent = String(m.ply);

      const sanEl = document.createElement("div");
      sanEl.className = "san";
      sanEl.textContent = m.ply === 0 ? "Start" : m.san || "";

      item.appendChild(plyEl);
      item.appendChild(sanEl);

      item.addEventListener("click", () => {
        // Stop playback when user manually interacts
        try {
          replay.pause();
        } catch (e) {
          // ignore: best-effort pause when interacting manually
          void e;
        }
        if (btnPlay) btnPlay.textContent = "Play";
        // Jump by API ply value so direct ply lookups work
        replay.jumpTo(m.ply);
        updateReplayView();
      });

      container.appendChild(item);
    });
    // ensure move-history visible when populated
    if (mh && !mh.classList.contains("hidden")) {
      // scroll current into view
      const current = container.querySelector(".move-item.current") as HTMLElement | null;
      if (current) current.scrollIntoView({ block: "nearest" });
    }
  }

  if (btnFirst)
    btnFirst.addEventListener("click", () => {
      replay.pause();
      if (btnPlay) btnPlay.textContent = "Play";
      replay.first();
      updateReplayView();
    });
  if (btnPrev)
    btnPrev.addEventListener("click", () => {
      replay.pause();
      if (btnPlay) btnPlay.textContent = "Play";
      replay.prev();
      updateReplayView();
    });
  if (btnNext)
    btnNext.addEventListener("click", () => {
      replay.pause();
      if (btnPlay) btnPlay.textContent = "Play";
      replay.next();
      updateReplayView();
    });
  if (btnLast)
    btnLast.addEventListener("click", () => {
      replay.pause();
      if (btnPlay) btnPlay.textContent = "Play";
      replay.last();
      updateReplayView();
    });
  if (btnJump && inputJump)
    btnJump.addEventListener("click", () => {
      try {
        replay.pause();
      } catch (e) {
        // ignore: best-effort pause when using jump control
        void e;
      }
      if (btnPlay) btnPlay.textContent = "Play";
      replay.jumpTo(Number(inputJump.value || 0));
      updateReplayView();
    });
  if (btnExitReplay) {
    btnExitReplay.addEventListener("click", () => {
      isReplayMode = false;
      if (replayControls) replayControls.classList.add("hidden");
      if (replayError) {
        replayError.textContent = "";
        replayError.classList.add("hidden");
      }
      // Clear replay state and return to the lobby main screen
      try {
        replay.clear();
      } catch {
        // ignore if clear not present
      }
      // hide move history panel
      const mh = document.getElementById("move-history");
      if (mh) mh.classList.add("hidden");
      // ensure playback stopped
      try {
        replay.pause();
      } catch (e) {
        // ignore: ensure playback stopped on exit
        void e;
      }
      if (btnPlay) btnPlay.textContent = "Play";
      if (replayModal) replayModal.classList.add("hidden");
      showLobby();
      showToast("Exited replay mode — back to lobby");
    });
  }

  // Play/Pause wiring
  if (btnPlay) {
    btnPlay.addEventListener("click", () => {
      if (!replay.doc) return;
      if (replay.isPlaying()) {
        replay.pause();
        btnPlay.textContent = "Play";
        return;
      }
      // start playback with selected speed
      const ms = selectSpeed ? Number(selectSpeed.value || 1000) : 1000;
      replay.play(ms, () => {
        updateReplayView();
        if (!replay.isPlaying()) {
          if (btnPlay) btnPlay.textContent = "Play";
        } else {
          if (btnPlay) btnPlay.textContent = "Pause";
        }
      });
      btnPlay.textContent = "Pause";
    });
  }
});

// --- WAKEUP OVERLAY DISMISSAL ENGINE ---
socket.on("connect", () => {
  console.log(`⚡ Connected to backend at ${BACKEND_URL}! ID:`, socket.id);

  const urlParams = new URLSearchParams(window.location.search);
  const roomFromUrl = urlParams.get("room")?.trim().toUpperCase();

  if (!roomFromUrl || roomFromUrl.length !== 4) {
    showLobby();
  }
  // Update connection UI
  if (connStatus) {
    connStatus.textContent = "Connected";
    connStatus.className = "conn-status connected";
  }
  const createBtn = btnCreateEl();
  if (createBtn) createBtn.disabled = false;
  const joinBtn = btnJoinEl();
  if (joinBtn) joinBtn.disabled = false;
  showToast("Connected");
  // hide retry button when connected
  setRetryVisible(false);
});

socket.on("disconnect", (reason) => {
  if (connStatus) {
    connStatus.textContent = "Disconnected";
    connStatus.className = "conn-status disconnected";
  }
  const createBtn = btnCreateEl();
  if (createBtn) createBtn.disabled = true;
  const joinBtn = btnJoinEl();
  if (joinBtn) joinBtn.disabled = true;
  console.log("Socket disconnected:", reason);
  showToast("Disconnected from server");
  // show retry button when disconnected
  setRetryVisible(true);
});

socket.on("connect_error", (err) => {
  if (connStatus) {
    connStatus.textContent = "Connecting";
    connStatus.className = "conn-status connecting";
  }
  console.warn("Connect error:", err);
});

// Setup Initial Render Board Frame State
renderBoard(board, selectedSquare, myRole);

// Handle Outbound Direct URL Actions
const urlParams = new URLSearchParams(window.location.search);
const roomFromUrl = urlParams.get("room")?.trim().toUpperCase();
if (roomFromUrl && roomFromUrl.length === 4) {
  const inputRoomCode = document.getElementById("input-room-code") as HTMLInputElement;
  if (inputRoomCode) inputRoomCode.value = roomFromUrl;
  socket.emit("join_room", { roomId: roomFromUrl });
}

// --- SOCKET ENGINE SYNCHRONIZATION ---
socket.on("assigned_role", (payload) => {
  const role = payload.color;
  myRole = role;
  currentMatchStatus = payload.status;
  currentTurn = payload.current_turn;
  if (roomDisplay) roomDisplay.textContent = payload.room_id;
  if (identityEl) {
    identityEl.textContent = role.toUpperCase();
    identityEl.style.color =
      role === "white" ? "#ffffff" : role === "black" ? "#000000" : "#6b7280";
  }
  for (let r = 0; r < 8; r++) board[r] = [...payload.board[r]];
  updateTurnHUD(payload);
  showGameRoom();
  renderBoard(board, selectedSquare, myRole);
  console.info(`[assigned_role] room=${payload.room_id} role=${role}`);
  // Update the URL with the active room so share links and reloads work
  if (payload.room_id && payload.room_id.length === 4) {
    try {
      const u = new URL(window.location.href);
      u.searchParams.set("room", payload.room_id);
      window.history.replaceState({}, "", u.toString());
    } catch {
      // ignore URL manipulation errors
    }
  }
});

socket.on("move_rejected", (payload) => {
  // Visual feedback for rejected moves
  console.warn(`Illegal Move: ${payload.reason}`);
  if (lastProposedFrom) {
    const sq = document.querySelector(
      `.square[data-row="${lastProposedFrom.row}"][data-col="${lastProposedFrom.col}"]`
    ) as HTMLElement;
    if (sq) {
      sq.classList.add("move-invalid");
      setTimeout(() => {
        sq.classList.remove("move-invalid");
        renderBoard(board, selectedSquare, myRole);
      }, 520);
    } else {
      renderBoard(board, selectedSquare, myRole);
    }
    lastProposedFrom = null;
  } else {
    renderBoard(board, selectedSquare, myRole);
  }
});

socket.on("move_executed", (payload) => {
  currentMatchStatus = payload.status;
  currentTurn = payload.current_turn;
  for (let r = 0; r < 8; r++) board[r] = [...payload.board[r]];
  updateTurnHUD(payload);
  selectedSquare = null;
  renderBoard(board, selectedSquare, myRole);
  if (payload.last_move) {
    const fm = payload.last_move.from;
    const to = payload.last_move.to;
    console.info(`[move_executed] from=${fmtCoord(fm.row, fm.col)} to=${fmtCoord(to.row, to.col)}`);
  } else {
    console.info("[move_executed] board updated");
  }
});

function updateTurnHUD(payload: {
  status: string;
  winner?: string;
  current_turn: string;
  check_status?: string;
}) {
  if (!turnEl) return;
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

// --- POINTER LAYER CAPTURE MACHINE ---
const boardContainer = document.getElementById("chess-board");
let activeDragPiece: HTMLElement | null = null;
let sourceSquare: { row: number; col: number } | null = null;
let lastProposedFrom: { row: number; col: number } | null = null;
let hasMovedSignificantly = false;
let startX = 0;
let startY = 0;
let dragClone: HTMLElement | null = null;
let activePieceImgOriginal: HTMLElement | null = null;
let isDragging = false;

if (boardContainer) {
  boardContainer.addEventListener("pointerdown", (event) => {
    if (
      currentMatchStatus === "completed" ||
      myRole === "spectator" ||
      myRole !== currentTurn ||
      isReplayMode
    )
      return;

    const target = event.target as HTMLElement;
    const squareEl = target.closest(".square") as HTMLElement;
    if (!squareEl) return;

    const row = parseInt(squareEl.dataset.row!, 10);
    const col = parseInt(squareEl.dataset.col!, 10);
    const clickedPiece = board[row][col];

    startX = event.clientX;
    startY = event.clientY;
    hasMovedSignificantly = false;

    if (inputPreference === "click") {
      handleSquareClick(row, col);
      return;
    }

    if (!clickedPiece) {
      if (inputPreference === "hybrid" && selectedSquare) {
        handleSquareClick(row, col);
      }
      return;
    }

    const pieceColorMapped = clickedPiece.color === "w" ? "white" : "black";
    if (pieceColorMapped !== myRole) {
      if (inputPreference === "hybrid" && selectedSquare) {
        handleSquareClick(row, col);
      }
      return;
    }

    // Prepare for a possible drag. Don't mutate DOM yet — we clone when drag starts.
    sourceSquare = { row, col };
    const pieceImg = squareEl.querySelector(".chess-piece") as HTMLElement;
    if (!pieceImg) return;

    activePieceImgOriginal = pieceImg;
    activeDragPiece = null;
    isDragging = false;
    dragClone = null;
    event.preventDefault();
    console.debug(`[pointerdown] source=${fmtCoord(row, col)}`);
  });

  boardContainer.addEventListener("pointermove", (event) => {
    if (!activePieceImgOriginal || !sourceSquare) return;

    if (!hasMovedSignificantly) {
      const deltaX = Math.abs(event.clientX - startX);
      const deltaY = Math.abs(event.clientY - startY);
      if (deltaX > 4 || deltaY > 4) {
        hasMovedSignificantly = true;

        if (inputPreference === "drag" || inputPreference === "hybrid") {
          // Create a floating clone for the drag visual so the board DOM remains untouched.
          dragClone = activePieceImgOriginal.cloneNode(true) as HTMLElement;
          dragClone.classList.add("is-dragging");
          dragClone.style.position = "fixed";
          dragClone.style.pointerEvents = "none";
          const squareEl = activePieceImgOriginal.parentElement as HTMLElement;
          dragClone.style.width = `${squareEl.offsetWidth * 0.85}px`;
          dragClone.style.height = `${squareEl.offsetHeight * 0.85}px`;
          document.body.appendChild(dragClone);
          // Hide the original piece so it appears to be picked up
          try {
            activePieceImgOriginal.style.visibility = "hidden";
          } catch (e) {
            console.debug(e);
          }
          boardContainer.setPointerCapture(event.pointerId);
          isDragging = true;
          activeDragPiece = dragClone;
          updatePiecePosition(event.clientX, event.clientY);
          if (sourceSquare)
            console.debug(`[dragstart] from=${fmtCoord(sourceSquare.row, sourceSquare.col)}`);
        }
      }
    } else if (isDragging && dragClone) {
      updatePiecePosition(event.clientX, event.clientY);
    }
  });

  boardContainer.addEventListener("pointerup", (event) => {
    // If the pointer never moved significantly, treat as a click
    if (!hasMovedSignificantly && sourceSquare) {
      cleanupDragStyles();
      // Only treat as a click when click input is allowed (click or hybrid)
      if (inputPreference !== "drag") {
        handleSquareClick(sourceSquare.row, sourceSquare.col);
      }
      sourceSquare = null;
      activePieceImgOriginal = null;
      return;
    }

    // End of a drag operation
    if (!activePieceImgOriginal || !sourceSquare) return;

    if (boardContainer.hasPointerCapture(event.pointerId)) {
      boardContainer.releasePointerCapture(event.pointerId);
    }

    // Determine drop target
    const dropTarget = document.elementFromPoint(
      event.clientX,
      event.clientY
    ) as HTMLElement | null;
    const targetSquare = dropTarget?.closest(".square") as HTMLElement | null;
    if (targetSquare) {
      const toRow = parseInt(targetSquare.dataset.row!, 10);
      const toCol = parseInt(targetSquare.dataset.col!, 10);

      if (sourceSquare.row !== toRow || sourceSquare.col !== toCol) {
        lastProposedFrom = { row: sourceSquare.row, col: sourceSquare.col };
        console.info(
          `[propose_move] from=${fmtCoord(sourceSquare.row, sourceSquare.col)} to=${fmtCoord(
            toRow,
            toCol
          )}`
        );
        socket.emit("propose_move", {
          from: { row: sourceSquare.row, col: sourceSquare.col },
          to: { row: toRow, col: toCol },
        });
      }
    }

    // Clean up clone and state
    cleanupDragStyles();
    sourceSquare = null;
    activePieceImgOriginal = null;
    activeDragPiece = null;
    isDragging = false;
    renderBoard(board, selectedSquare, myRole);
  });

  function cleanupDragStyles() {
    if (dragClone && dragClone.parentElement) {
      try {
        dragClone.parentElement.removeChild(dragClone);
      } catch (e) {
        console.debug(e);
      }
    }
    dragClone = null;
    // Restore original piece visibility if it was hidden
    if (activePieceImgOriginal) {
      try {
        activePieceImgOriginal.style.visibility = "";
      } catch (e) {
        console.debug(e);
      }
    }
    if (activeDragPiece) {
      activeDragPiece.classList.remove("is-dragging");
      activeDragPiece.style.position = "";
      activeDragPiece.style.left = "";
      activeDragPiece.style.top = "";
      activeDragPiece.style.width = "";
      activeDragPiece.style.height = "";
    }
    isDragging = false;
  }

  function handleSquareClick(row: number, col: number) {
    if (isReplayMode) return; // prevent proposing moves while replaying
    if (isDragging) return; // ignore clicks while dragging
    const clickedPiece = board[row][col];

    if (selectedSquare === null) {
      if (clickedPiece && (clickedPiece.color === "w" ? "white" : "black") === myRole) {
        selectedSquare = { row, col };
        renderBoard(board, selectedSquare, myRole);
        console.debug(`[select] selected=${fmtCoord(row, col)}`);
      }
    } else {
      if (selectedSquare.row === row && selectedSquare.col === col) {
        selectedSquare = null;
        renderBoard(board, selectedSquare, myRole);
      } else if (clickedPiece && (clickedPiece.color === "w" ? "white" : "black") === myRole) {
        selectedSquare = { row, col };
        renderBoard(board, selectedSquare, myRole);
      } else {
        lastProposedFrom = { row: selectedSquare.row, col: selectedSquare.col };
        console.info(
          `[propose_move] from=${fmtCoord(selectedSquare.row, selectedSquare.col)} to=${fmtCoord(
            row,
            col
          )}`
        );
        socket.emit("propose_move", {
          from: { row: selectedSquare.row, col: selectedSquare.col },
          to: { row, col },
        });
        selectedSquare = null;
      }
    }
  }

  function updatePiecePosition(clientX: number, clientY: number) {
    if (!activeDragPiece) return;
    activeDragPiece.style.left = `${clientX - activeDragPiece.offsetWidth / 2}px`;
    activeDragPiece.style.top = `${clientY - activeDragPiece.offsetHeight / 2}px`;
  }
}
