import { beforeEach, describe, expect, it, vi } from "vitest";

const socketState = vi.hoisted(() => {
  const handlers = new Map<string, (...args: any[]) => void>();
  const emits: Array<[string, any]> = [];

  const socket = {
    connected: true,
    id: "socket-1",
    on: vi.fn((event: string, handler: (...args: any[]) => void) => {
      handlers.set(event, handler);
      return socket;
    }),
    emit: vi.fn((event: string, payload?: any) => {
      emits.push([event, payload]);
      return socket;
    }),
    connect: vi.fn(),
    disconnect: vi.fn(),
  };

  return { handlers, emits, socket };
});

vi.mock("socket.io-client", () => ({
  io: vi.fn(() => socketState.socket),
}));

vi.mock("../src/renderer", () => ({
  renderBoard: vi.fn(),
}));

vi.mock("../src/replay", () => ({
  default: class FakeReplayController {
    getCurrentBoard() {
      return null;
    }

    getDisplayPly() {
      return 0;
    }

    getMaxPly() {
      return 0;
    }

    isLoaded() {
      return false;
    }

    isPlaying() {
      return false;
    }

    loadGame() {
      return Promise.resolve();
    }

    first() {}

    prev() {}

    next() {}

    last() {}

    jumpToPly() {}

    play() {}

    pause() {}
  },
}));

vi.mock("../src/replay-ui", () => ({
  renderMoveHistory: vi.fn(),
}));

vi.mock("../src/import-ui", () => ({
  default: vi.fn(),
}));

function mountLobby() {
  document.body.innerHTML = `
    <div id="server-loader"></div>
    <div id="lobby-screen"></div>
    <div id="app-container"></div>
    <div id="player-identity"></div>
    <div id="turn-indicator"></div>
    <div id="room-display"></div>
    <div id="settings-modal"></div>
    <button id="btn-settings"></button>
    <button id="btn-close-settings"></button>
    <select id="select-input-mode"></select>
    <button id="btn-retry"></button>
    <button id="btn-copy-link"></button>
    <div id="conn-status"></div>
    <button id="btn-create">Create Private Match</button>
    <button id="btn-bot-create">Create Bot Match</button>
    <input id="input-room-code" />
    <button id="btn-join">Join Game</button>
    <button id="btn-open-replay-lobby"></button>
    <button id="btn-open-replay"></button>
    <div id="replay-controls"></div>
    <button id="btn-first"></button>
    <button id="btn-prev"></button>
    <button id="btn-next"></button>
    <button id="btn-last"></button>
    <button id="btn-play"></button>
    <select id="select-speed"></select>
    <button id="btn-jump"></button>
    <input id="replay-jump" />
    <div id="replay-status"></div>
    <button id="btn-exit-replay"></button>
    <div id="replay-modal"></div>
    <input id="replay-game-id" />
    <select id="replay-source-type"></select>
    <button id="btn-load-replay"></button>
    <div id="replay-error"></div>
    <div id="replay-list"></div>
    <button id="btn-close-replay-modal"></button>
    <div id="import-modal"></div>
    <button id="btn-open-import"></button>
    <button id="btn-close-import"></button>
    <input id="import-file" />
    <textarea id="import-text"></textarea>
    <button id="btn-import-submit"></button>
    <div id="import-result"></div>
    <div id="chess-board"></div>
  `;
  localStorage.setItem("chess_user_id", "test-user");
}

describe("main lobby actions", () => {
  beforeEach(() => {
    socketState.emits.length = 0;
    socketState.handlers.clear();
    socketState.socket.emit.mockClear();
    socketState.socket.on.mockClear();
    socketState.socket.connect.mockClear();
    socketState.socket.connected = true;
    document.body.innerHTML = "";
    mountLobby();
  });

  it("emits create_room and create_bot_room from the lobby buttons", async () => {
    await import("../src/main");
    document.dispatchEvent(new Event("DOMContentLoaded"));

    (document.getElementById("btn-create") as HTMLButtonElement).click();
    (document.getElementById("btn-bot-create") as HTMLButtonElement).click();

    expect(socketState.emits).toContainEqual(["create_room", undefined]);
    expect(socketState.emits).toContainEqual(["create_bot_room", undefined]);
  });
});
