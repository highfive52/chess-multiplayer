import type ReplayController from "./replay";

export function renderMoveHistory(
  controller: InstanceType<typeof ReplayController>,
  btnPlayId?: string
) {
  const container = document.getElementById("move-list");
  const mh = document.getElementById("move-history");
  const btnPlay = btnPlayId ? document.getElementById(btnPlayId) : null;
  if (!container || !controller?.doc) return;
  container.innerHTML = "";
  const moves = controller.doc.moves;
  moves.forEach((m, idx) => {
    const item = document.createElement("div");
    item.className = "move-item";
    if (idx === controller.currentPly) item.classList.add("current");

    const plyEl = document.createElement("div");
    plyEl.className = "ply";
    plyEl.textContent = String(m.ply);

    const sanEl = document.createElement("div");
    sanEl.className = "san";
    sanEl.textContent = m.ply === 0 ? "Start" : m.san || "";

    item.appendChild(plyEl);
    item.appendChild(sanEl);

    item.addEventListener("click", () => {
      try {
        controller.pause();
      } catch (e) {
        void e;
      }
      if (btnPlay) btnPlay.textContent = "Play";
      controller.jumpTo(m.ply);
      // Notify interested parties (e.g. the main view) that a jump occurred
      try {
        document.dispatchEvent(new CustomEvent("replay:jump", { detail: { ply: m.ply } }));
      } catch (e) {
        // ignore if dispatch fails in non-browser test envs
        void e;
      }
    });

    container.appendChild(item);
  });

  if (mh && !mh.classList.contains("hidden")) {
    const current = container.querySelector(".move-item.current") as HTMLElement | null;
    if (current && "scrollIntoView" in current && typeof current.scrollIntoView === "function") {
      current.scrollIntoView({ block: "nearest" });
    }
  }
}

export default renderMoveHistory;
