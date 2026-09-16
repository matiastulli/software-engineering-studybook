/* Diagram zoom: opens a rendered Mermaid SVG in a pan/zoom overlay.
   Mounted on the viewer shell — reuses #app for the inert backdrop. Exposes
   window.__enhanceDiagrams(), which renderMermaid() calls after every run. */
(() => {
  "use strict";
  const q$ = (s, r = document) => r.querySelector(s);
  const MIN = 0.1, MAX = 8;

  let overlay, stage, canvas, pct, titleEl;
  let scale = 1, tx = 0, ty = 0;          // current transform
  let natural = { w: 0, h: 0 };            // unscaled diagram size
  let lastFocus = null;

  function build() {
    overlay = document.createElement("div");
    overlay.id = "dz";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-label", "Diagram viewer");
    overlay.innerHTML = `
      <div class="dz-bar">
        <span class="dz-title"></span>
        <span class="dz-hint">scroll to zoom · drag to pan · <kbd>Esc</kbd> to close</span>
        <button class="dz-btn" data-act="out" title="Zoom out (−)" aria-label="Zoom out">−</button>
        <span class="dz-pct" aria-live="polite" aria-atomic="true">100%</span>
        <button class="dz-btn" data-act="in" title="Zoom in (+)" aria-label="Zoom in">+</button>
        <button class="dz-btn" data-act="fit" title="Fit to screen (0)" aria-label="Fit to screen">⤢</button>
        <button class="dz-btn" data-act="close" title="Close (Esc)" aria-label="Close diagram viewer">✕</button>
      </div>
      <div class="dz-stage"><div class="dz-canvas"></div></div>`;
    document.body.appendChild(overlay);

    stage = q$(".dz-stage", overlay);
    canvas = q$(".dz-canvas", overlay);
    pct = q$(".dz-pct", overlay);
    titleEl = q$(".dz-title", overlay);

    overlay.addEventListener("click", e => {
      const b = e.target.closest("[data-act]");
      if (b) {
        const a = b.dataset.act;
        if (a === "close") close();
        else if (a === "fit") fit();
        else zoomBy(a === "in" ? 1.25 : 1 / 1.25);
        return;
      }
      if (e.target === stage) close();          // click the empty backdrop
    });

    // wheel zoom, anchored on the pointer so the diagram does not drift away
    stage.addEventListener("wheel", e => {
      e.preventDefault();
      const r = stage.getBoundingClientRect();
      zoomAt(e.clientX - r.left, e.clientY - r.top, Math.exp(-e.deltaY * 0.0015));
    }, { passive: false });

    // drag to pan (pointer events cover mouse, pen and touch)
    let drag = null;
    stage.addEventListener("pointerdown", e => {
      if (e.button !== 0) return;
      drag = { x: e.clientX, y: e.clientY, tx, ty };
      stage.setPointerCapture(e.pointerId);
      stage.classList.add("drag");
    });
    stage.addEventListener("pointermove", e => {
      if (!drag) return;
      tx = drag.tx + (e.clientX - drag.x);
      ty = drag.ty + (e.clientY - drag.y);
      apply();
    });
    const endDrag = () => { drag = null; stage.classList.remove("drag"); };
    stage.addEventListener("pointerup", endDrag);
    stage.addEventListener("pointercancel", endDrag);

    // pinch zoom
    let pinch = null;
    stage.addEventListener("touchstart", e => {
      if (e.touches.length === 2) pinch = { d: dist(e.touches), s: scale };
    }, { passive: true });
    stage.addEventListener("touchmove", e => {
      if (pinch && e.touches.length === 2) {
        e.preventDefault();
        const r = stage.getBoundingClientRect();
        const cx = (e.touches[0].clientX + e.touches[1].clientX) / 2 - r.left;
        const cy = (e.touches[0].clientY + e.touches[1].clientY) / 2 - r.top;
        zoomAt(cx, cy, (dist(e.touches) / pinch.d) * pinch.s / scale);
      }
    }, { passive: false });
    stage.addEventListener("touchend", () => { pinch = null; });
  }

  const dist = t => Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY);
  const isOpen = () => overlay && overlay.classList.contains("open");

  function apply() {
    canvas.style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`;
    pct.textContent = Math.round(scale * 100) + "%";
  }

  function zoomAt(px, py, factor) {
    const next = Math.min(MAX, Math.max(MIN, scale * factor));
    if (next === scale) return;
    // keep the point under the cursor fixed
    tx = px - (px - tx) * (next / scale);
    ty = py - (py - ty) * (next / scale);
    scale = next;
    apply();
  }

  function zoomBy(factor) {
    const r = stage.getBoundingClientRect();
    zoomAt(r.width / 2, r.height / 2, factor);
  }

  function fit() {
    const r = stage.getBoundingClientRect();
    const pad = 32;
    if (!natural.w || !natural.h) return;
    scale = Math.min((r.width - pad) / natural.w, (r.height - pad) / natural.h, MAX);
    scale = Math.max(scale, MIN);
    tx = (r.width - natural.w * scale) / 2;
    ty = (r.height - natural.h * scale) / 2;
    apply();
  }

  function open(pre, label, trigger) {
    const svg = pre.querySelector("svg");
    if (!svg) return;
    if (!overlay) build();

    const clone = svg.cloneNode(true);
    clone.removeAttribute("style");
    // Prefer the viewBox for natural size: Mermaid writes a percentage width.
    const vb = (clone.getAttribute("viewBox") || "").split(/[\s,]+/).map(Number);
    let w = vb.length === 4 && vb[2] ? vb[2] : svg.getBoundingClientRect().width;
    let h = vb.length === 4 && vb[3] ? vb[3] : svg.getBoundingClientRect().height;
    if (!w || !h) { w = svg.getBoundingClientRect().width; h = svg.getBoundingClientRect().height; }
    clone.setAttribute("width", w);
    clone.setAttribute("height", h);
    natural = { w: w + 36, h: h + 36 };      // + the .dz-canvas svg padding

    canvas.replaceChildren(clone);
    titleEl.textContent = label || "Diagram";

    lastFocus = trigger || pre.querySelector(".dz-open") || document.activeElement;
    overlay.classList.add("open");
    const app = q$("#app"); if (app) app.setAttribute("inert", "");
    // measure after the overlay is displayed, otherwise the stage has no size yet
    requestAnimationFrame(() => { fit(); q$('[data-act="close"]', overlay).focus(); });
  }

  function close() {
    if (!isOpen()) return;
    overlay.classList.remove("open");
    canvas.replaceChildren();
    const app = q$("#app"); if (app) app.removeAttribute("inert");
    // blur first: the close button is about to be display:none, which strands focus
    if (document.activeElement && overlay.contains(document.activeElement))
      document.activeElement.blur();
    if (lastFocus && lastFocus.isConnected && typeof lastFocus.focus === "function") lastFocus.focus();
    lastFocus = null;
  }

  /* Capture phase: the viewer and the mix module both listen for these keys. */
  addEventListener("keydown", e => {
    if (!isOpen()) return;
    if (e.ctrlKey || e.metaKey) return;
    const k = e.key;
    const step = e.shiftKey ? 120 : 45;
    const stop = () => { e.preventDefault(); e.stopPropagation(); };
    if (k === "Escape") { close(); stop(); }
    else if (k === "+" || k === "=") { zoomBy(1.25); stop(); }
    else if (k === "-" || k === "_") { zoomBy(1 / 1.25); stop(); }
    else if (k === "0") { fit(); stop(); }
    else if (k === "ArrowLeft") { tx += step; apply(); stop(); }
    else if (k === "ArrowRight") { tx -= step; apply(); stop(); }
    else if (k === "ArrowUp") { ty += step; apply(); stop(); }
    else if (k === "ArrowDown") { ty -= step; apply(); stop(); }
    // Everything else is swallowed too: j/k/t/m would otherwise drive the document
    // and the mix module underneath an overlay that is covering the whole screen.
    else stop();
  }, true);

  addEventListener("resize", () => { if (isOpen()) fit(); });

  /* ---------- wiring ---------- */
  function labelFor(pre) {
    // the nearest preceding heading gives the diagram a meaningful name
    let n = pre.previousElementSibling;
    while (n) {
      if (/^H[1-4]$/.test(n.tagName)) return n.textContent.replace(/#$/, "").trim();
      n = n.previousElementSibling;
    }
    return "Diagram";
  }

  function enhance() {
    for (const pre of document.querySelectorAll("#doc pre.mermaid[data-processed]")) {
      if (!pre.querySelector("svg")) continue;
      if (pre.querySelector(".dz-open")) continue;         // already wired
      const label = labelFor(pre);

      const btn = document.createElement("button");
      btn.className = "dz-open";
      btn.type = "button";
      btn.innerHTML = "⤢ <span>Expand</span>";
      btn.setAttribute("aria-label", "Expand diagram: " + label);
      btn.addEventListener("click", e => { e.stopPropagation(); open(pre, label, btn); });
      pre.appendChild(btn);

      pre.addEventListener("click", e => {
        if (e.target.closest(".dz-open")) return;
        open(pre, label, btn);
      });
    }
  }

  window.__enhanceDiagrams = enhance;
  window.__diagramZoomOpen = isOpen;
})();
