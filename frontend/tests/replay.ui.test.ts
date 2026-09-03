import { describe, it, expect, beforeEach } from "vitest";
import { fireEvent } from "@testing-library/dom";
import renderMoveHistory from "../src/replay-ui";

class StubController {
  constructor(public doc: any) {}
  currentPly = 0;
  pause() {}
  jumpTo(p: number) {
    this.currentPly = p;
  }
}

describe("renderMoveHistory", () => {
  beforeEach(() => {
    document.body.innerHTML =
      '<div id="move-history"><div id="move-list"></div></div><button id="btn-play">Play</button>';
  });

  it("renders SAN list and responds to clicks", () => {
    const doc = {
      moves: [
        { ply: 0, san: "", fen_after: "f0" },
        { ply: 1, san: "e4", fen_after: "f1" },
      ],
    };
    const c = new StubController(doc);
    renderMoveHistory(c as any, "btn-play");
    const items = document.querySelectorAll(".move-item");
    expect(items.length).toBe(2);
    const second = items[1] as HTMLElement;
    fireEvent.click(second);
    expect(c.currentPly).toBe(1);
  });
});
