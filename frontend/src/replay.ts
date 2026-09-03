import type { BoardMatrix } from "./types";
import { fenToBoard } from "./chess/fen";

type Move = {
  ply: number;
  san: string;
  fen_after: string;
  created_at?: string;
};

type ReplayDoc = {
  game_id: string;
  initial_fen?: string | null;
  status?: string | null;
  result?: string | null;
  moves: Move[];
};

export class ReplayController {
  baseUrl: string;
  doc: ReplayDoc | null = null;
  currentPly = 0;
  private playbackTimer: number | null = null;
  private playing: boolean = false;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async load(gameId: string): Promise<void> {
    const url = `${this.baseUrl}/games/${gameId}/replay`;
    console.debug("Fetching replay URL:", url);
    let resp: Response;
    try {
      resp = await fetch(url, { mode: "cors" });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      const out = new Error(`network error fetching replay ${url}: ${msg}`);
      try {
        // Attach the original error as `cause` when possible to preserve context
        (out as Error & { cause?: unknown }).cause = err;
      } catch {
        // ignore
      }
      throw out;
    }
    if (!resp.ok) throw new Error(`failed to load replay: ${resp.status}`);
    this.doc = await resp.json();
    // Align currentPly to the index of the synthetic ply 0 (if present)
    const idx0 = this.doc!.moves.findIndex((m) => m.ply === 0);
    this.currentPly = idx0 >= 0 ? idx0 : 0;
    // loaded
  }

  // Return the ply value for the currently selected move (from API `ply` field)
  getDisplayPly(): number {
    if (!this.doc) return 0;
    const idx = this.currentPly;
    if (idx < 0 || idx >= this.doc.moves.length) return 0;
    return this.doc.moves[idx].ply;
  }

  // Return the maximum ply value present in the document (not the array length)
  getMaxPly(): number {
    if (!this.doc || this.doc.moves.length === 0) return 0;
    return Math.max(...this.doc.moves.map((m) => m.ply));
  }

  // Return the maximum ply value available (e.g. if moves has 5 items, last ply is 4)
  getMovesCount(): number {
    if (!this.doc) return 0;
    return Math.max(0, this.doc.moves.length - 1);
  }

  // Explicit alias for the last valid ply index
  getLastPly(): number {
    return this.getMovesCount();
  }

  getCurrentFen(): string | null {
    if (!this.doc) return null;
    const idx = this.currentPly;
    if (idx < 0 || idx >= this.doc.moves.length) return null;
    const move = this.doc.moves[idx];
    // Prefer the move's FEN; if missing and this is the synthetic ply 0,
    // fall back to document-level `initial_fen` when available.
    if (move.fen_after) return move.fen_after;
    if (move.ply === 0 && this.doc.initial_fen) return this.doc.initial_fen;
    return null;
  }

  getCurrentBoard(): BoardMatrix | null {
    const fen = this.getCurrentFen();
    if (!fen) return null;
    try {
      return fenToBoard(fen);
    } catch (e) {
      // Non-fatal: log and return null so UI can handle missing/invalid FEN
      // (some persisted rows may be empty or malformed in edge cases).
      console.warn("Invalid FEN while building board:", fen, e);
      return null;
    }
  }

  first() {
    this.currentPly = 0;
  }

  prev() {
    this.currentPly = Math.max(0, this.currentPly - 1);
  }

  next() {
    if (!this.doc) return;
    const last = Math.max(0, this.doc.moves.length - 1);
    this.currentPly = Math.min(last, this.currentPly + 1);
  }

  last() {
    if (!this.doc) return;
    this.currentPly = Math.max(0, this.doc.moves.length - 1);
  }

  jumpTo(ply: number) {
    if (!this.doc) return;
    // Try to interpret the argument as an API `ply` value and map it
    // to the corresponding move array index. This keeps UI callers
    // able to pass either a ply number or an index.
    const idx = this.doc.moves.findIndex((m) => m.ply === ply);
    if (idx >= 0) {
      this.currentPly = idx;
      return;
    }
    // Fallback: treat as an index and clamp into bounds
    const last = Math.max(0, this.doc.moves.length - 1);
    const clamped = Math.max(0, Math.min(last, Math.floor(ply)));
    this.currentPly = clamped;
  }

  // Clear loaded replay state
  clear() {
    this.doc = null;
    this.currentPly = 0;
  }

  // Playback controls: start automatic advancement at `intervalMs` milliseconds.
  // Accepts an optional `onTick` callback invoked after each advance (or when playback stops).
  play(intervalMs: number = 1000, onTick?: () => void) {
    if (this.playbackTimer != null) return; // already playing
    this.playing = true;
    this.playbackTimer = window.setInterval(() => {
      if (!this.doc) {
        this.pause();
        if (onTick) onTick();
        return;
      }
      const last = Math.max(0, this.doc.moves.length - 1);
      if (this.currentPly >= last) {
        // reached the end — stop playback
        this.pause();
        if (onTick) onTick();
        return;
      }
      this.next();
      if (onTick) onTick();
    }, intervalMs) as unknown as number;
  }

  pause() {
    if (this.playbackTimer != null) {
      clearInterval(this.playbackTimer);
      this.playbackTimer = null;
    }
    this.playing = false;
  }

  isPlaying(): boolean {
    return this.playing;
  }
}

export default ReplayController;
