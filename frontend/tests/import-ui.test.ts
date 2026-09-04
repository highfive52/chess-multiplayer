import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, waitFor } from "@testing-library/dom";
import initImportUI from "../src/import-ui";

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
};

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

function mountUi() {
  document.body.innerHTML = `
    <button id="btn-open-import">Import PGN</button>
    <div id="import-modal" class="hidden">
      <button id="btn-close-import">Close</button>
      <input id="import-file" type="file" />
      <textarea id="import-text"></textarea>
      <button id="btn-import-submit">Import</button>
      <div id="import-result"></div>
    </div>
  `;
}

describe("import-ui", () => {
  beforeEach(() => {
    mountUi();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("opens and closes the import modal", () => {
    initImportUI("http://backend.test");

    const modal = document.getElementById("import-modal") as HTMLElement;
    fireEvent.click(document.getElementById("btn-open-import") as HTMLElement);
    expect(modal.classList.contains("hidden")).toBe(false);

    fireEvent.click(document.getElementById("btn-close-import") as HTMLElement);
    expect(modal.classList.contains("hidden")).toBe(true);
  });

  it("submits an uploaded PGN file and renders warnings and multiple games", async () => {
    const fetchDeferred = deferred<Response>();
    vi.spyOn(globalThis, "fetch").mockReturnValue(fetchDeferred.promise);

    initImportUI("http://backend.test");

    const file = new File(['[Event "Upload"]\n\n1. e4 e5 1-0\n'], "sample.pgn", {
      type: "text/plain",
    });
    const fileInput = document.getElementById("import-file") as HTMLInputElement;
    Object.defineProperty(fileInput, "files", {
      configurable: true,
      value: [file],
    });

    const submitBtn = document.getElementById("btn-import-submit") as HTMLButtonElement;
    fireEvent.click(submitBtn);
    expect(submitBtn.disabled).toBe(true);

    fetchDeferred.resolve({
      json: async () => ({
        imported: [
          { game_index: 1, game_id: "g-1", move_count: 4, warnings: ["COMMENTS_IGNORED"] },
          { game_index: 2, game_id: "g-2", move_count: 6, warnings: [] },
        ],
        failed: [],
      }),
    } as Response);

    await waitFor(() => {
      expect(submitBtn.disabled).toBe(false);
    });
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);

    await waitFor(() => {
      expect((document.getElementById("import-result") as HTMLElement).textContent).toContain(
        "Imported 2 games"
      );
    });
    expect((document.getElementById("import-result") as HTMLElement).textContent).toContain(
      "Warnings: COMMENTS_IGNORED"
    );
    expect((document.getElementById("import-result") as HTMLElement).textContent).toContain(
      "Game #2"
    );
  });

  it("submits pasted PGN text and renders failed imports", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      json: async () => ({
        imported: [],
        failed: [{ game_index: 1, code: "IMPORT_ERROR", message: "bad pgn" }],
      }),
    } as Response);

    initImportUI("http://backend.test");

    const textArea = document.getElementById("import-text") as HTMLTextAreaElement;
    textArea.value = '[Event "Paste"]\n\n1. e4 e5 1-0\n';

    fireEvent.click(document.getElementById("btn-import-submit") as HTMLElement);

    await waitFor(() => {
      expect((document.getElementById("import-result") as HTMLElement).textContent).toContain(
        "Failed to import 1 games"
      );
    });
    expect((document.getElementById("import-result") as HTMLElement).textContent).toContain(
      "bad pgn"
    );
  });

  it("renders a server error message when the request fails", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("boom"));

    initImportUI("http://backend.test");

    const textArea = document.getElementById("import-text") as HTMLTextAreaElement;
    textArea.value = '[Event "Fail"]\n\n1. e4 e5 1-0\n';

    fireEvent.click(document.getElementById("btn-import-submit") as HTMLElement);

    await waitFor(() => {
      expect((document.getElementById("import-result") as HTMLElement).textContent).toContain(
        "Error: boom"
      );
    });
  });
});
