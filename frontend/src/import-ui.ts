export default function initImportUI(backendUrl: string) {
  const openBtn = document.getElementById("btn-open-import");
  const modal = document.getElementById("import-modal");
  const closeBtn = document.getElementById("btn-close-import");
  const fileInput = document.getElementById("import-file") as HTMLInputElement | null;
  const textArea = document.getElementById("import-text") as HTMLTextAreaElement | null;
  const submitBtn = document.getElementById("btn-import-submit");
  const resultEl = document.getElementById("import-result");

  if (!openBtn || !modal) return;

  openBtn.addEventListener("click", () => {
    modal.classList.remove("hidden");
    if (textArea) textArea.focus();
  });
  if (closeBtn) closeBtn.addEventListener("click", () => modal.classList.add("hidden"));

  type ImportedGameSummary = {
    game_index: number;
    game_id: string;
    move_count: number;
    warnings?: string[];
  };

  type FailedGameSummary = {
    game_index: number;
    code: string;
    message: string;
    ply?: number;
  };

  type ImportResponse = {
    imported?: ImportedGameSummary[];
    failed?: FailedGameSummary[];
  };

  async function showResult(json: ImportResponse) {
    if (!resultEl) return;
    resultEl.innerHTML = "";
    if (json.imported && json.imported.length) {
      const h = document.createElement("div");
      h.className = "note";
      h.textContent = `Imported ${json.imported.length} games`;
      resultEl.appendChild(h);
      json.imported.forEach((g) => {
        const d = document.createElement("div");
        d.style.padding = "8px";
        d.style.borderBottom = "1px solid #222";
        d.innerHTML = `<strong>Game #${g.game_index}</strong> — id: ${g.game_id} — moves: ${g.move_count}`;
        if (g.warnings && g.warnings.length) {
          const w = document.createElement("div");
          w.style.marginTop = "6px";
          w.innerHTML = `<em>Warnings:</em> ${g.warnings.join(", ")}`;
          d.appendChild(w);
        }
        resultEl.appendChild(d);
      });
    }
    if (json.failed && json.failed.length) {
      const h = document.createElement("div");
      h.className = "note error";
      h.textContent = `Failed to import ${json.failed.length} games`;
      resultEl.appendChild(h);
      json.failed.forEach((f) => {
        const d = document.createElement("div");
        d.style.padding = "8px";
        d.style.borderBottom = "1px solid #222";
        d.innerHTML = `<strong>Game #${f.game_index}</strong> — code: ${f.code} — ${f.message}`;
        if (f.ply !== undefined) {
          const p = document.createElement("div");
          p.style.marginTop = "6px";
          p.textContent = `Ply: ${f.ply}`;
          d.appendChild(p);
        }
        resultEl.appendChild(d);
      });
    }
  }

  if (!submitBtn) return;
  submitBtn.addEventListener("click", async () => {
    submitBtn.setAttribute("disabled", "true");
    try {
      // Prefer file upload if present
      if (fileInput && fileInput.files && fileInput.files.length > 0) {
        const fd = new FormData();
        fd.append("file", fileInput.files[0]);
        const resp = await fetch(`${backendUrl}/games/import/pgn`, {
          method: "POST",
          body: fd,
        });
        const json = await resp.json();
        await showResult(json);
      } else if (textArea && textArea.value.trim()) {
        const resp = await fetch(`${backendUrl}/games/import/pgn`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: textArea.value }),
        });
        const json = await resp.json();
        await showResult(json);
      } else {
        alert("Please provide a .pgn file or paste PGN text");
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      if (resultEl) resultEl.textContent = `Error: ${msg}`;
    } finally {
      submitBtn.removeAttribute("disabled");
    }
  });
}
