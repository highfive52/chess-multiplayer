import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import ReplayController from "../src/replay";

describe("ReplayController", () => {
  let rc: ReplayController;

  beforeEach(() => {
    rc = new ReplayController("http://example.com");
  });

  it("maps jumpTo by ply and index", () => {
    rc.doc = {
      game_id: "g",
      initial_fen: null,
      status: null,
      result: null,
      moves: [
        { ply: 0, san: "", fen_after: "f0" },
        { ply: 1, san: "e4", fen_after: "f1" },
      ],
    };
    rc.jumpTo(1); // API ply
    expect(rc.getDisplayPly()).toBe(1);
    rc.jumpTo(0);
    expect(rc.getDisplayPly()).toBe(0);
  });

  it("plays and stops at final ply", () => {
    vi.useFakeTimers();
    rc.doc = {
      game_id: "g",
      initial_fen: null,
      status: null,
      result: null,
      moves: [
        { ply: 0, san: "", fen_after: "f0" },
        { ply: 1, san: "e4", fen_after: "f1" },
      ],
    };
    rc.play(1000);
    // advance past one interval
    vi.advanceTimersByTime(1500);
    expect(rc.getDisplayPly()).toBe(1);
    // advance further to ensure it stops
    vi.advanceTimersByTime(2000);
    expect(rc.isPlaying()).toBe(false);
    vi.useRealTimers();
  });
});
