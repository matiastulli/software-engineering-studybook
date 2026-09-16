/* ============================================================
   Mix mode — builds a run of questions drawn across topics.
   Lee window.__BANK__ (generado por tools/build-studybook.mjs) y
   se monta sobre el shell del visor: reusa #doc, toast() y open().
   ============================================================ */
(function () {
  const BANK = window.__BANK__;
  if (!BANK || !BANK.questions.length) return;

  const q$ = (s, r = document) => r.querySelector(s);
  const K = { presets: "ip-mix-presets", missed: "ip-mix-missed", cfg: "ip-mix-cfg" };
  const read = (k, d) => { try { const v = JSON.parse(localStorage.getItem(k)); return v ?? d; } catch { return d; } };
  const save = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} };
  const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  const QS = BANK.questions;
  const ALL_SECTIONS = BANK.topics.flatMap(t => t.sections.map(s => s.id));

  let missed = read(K.missed, {});
  let presets = read(K.presets, []);
  let cfg = Object.assign(
    { sel: ALL_SECTIONS.slice(), count: 20, order: "random", timer: 0, drills: true, onlyMissed: false },
    read(K.cfg, {})
  );
  cfg.sel = cfg.sel.filter(id => ALL_SECTIONS.includes(id));
  if (!cfg.sel.length) cfg.sel = ALL_SECTIONS.slice();

  // The shell starts on #welcome; keep it so we can return there on exit.
  const WELCOME = (document.querySelector("#welcome") || {}).outerHTML || "";

  const run = { on: false, queue: [], i: 0, shown: false, res: {}, left: 0, tick: null, done: false };

  /* ---------------- selection ---------------- */
  const missedCount = () => QS.filter(q => missed[q.id]).length;

  function pool() {
    const sel = new Set(cfg.sel);
    return QS.filter(q =>
      sel.has(q.sectionId) &&
      (cfg.drills || q.kind !== "drill") &&
      (!cfg.onlyMissed || missed[q.id]));
  }

  function shuffle(a) {
    const r = a.slice();
    for (let i = r.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [r[i], r[j]] = [r[j], r[i]]; }
    return r;
  }

  /* ---------------- dialog ---------------- */
  let modal = null;

  function buildModal() {
    modal = document.createElement("div");
    modal.id = "mix-modal";
    modal.innerHTML = `
      <div class="mx-back"></div>
      <div class="mx-card" role="dialog" aria-modal="true" aria-label="Question mix">
        <header>
          <div style="flex:1">
            <h3>🎲 Question mix</h3>
            <p>Pick the topics you expect to be asked about in <em>this</em> interview.</p>
          </div>
          <button class="icon-btn" id="mx-close" title="Close (Esc)">✕</button>
        </header>
        <div class="mx-body"></div>
        <footer>
          <span class="mx-tally"></span>
          <button class="mx-ghost" id="mx-cancel">Cancel</button>
          <button class="mx-go" id="mx-start">Start</button>
        </footer>
      </div>`;
    document.body.appendChild(modal);
    q$(".mx-back", modal).onclick = closeModal;
    q$("#mx-close", modal).onclick = closeModal;
    q$("#mx-cancel", modal).onclick = closeModal;
    q$("#mx-start", modal).onclick = start;
  }

  const isOpen = () => modal && modal.classList.contains("open");

  function openModal() {
    if (!modal) buildModal();
    renderModal();
    modal.classList.add("open");
  }
  function closeModal() { if (modal) modal.classList.remove("open"); }

  function renderModal() {
    const body = q$(".mx-body", modal);
    const sel = new Set(cfg.sel);
    const nMissed = missedCount();

    const topics = BANK.topics.map(t => {
      const on = t.sections.filter(s => sel.has(s.id)).length;
      const st = on === 0 ? "" : (on === t.sections.length ? "checked" : "indeterminate");
      return `
        <div>
          <div class="mx-topic" data-topic="${t.key}">
            <input type="checkbox" data-topic-cb="${t.key}" ${st === "checked" ? "checked" : ""}>
            <span class="nm" data-topic-lbl="${t.key}">${t.icon} ${esc(t.label)}</span>
            <span class="n">${t.count}</span>
            <button class="exp" data-exp="${t.key}" title="Show sections">▶</button>
          </div>
          <div class="mx-sub" data-sub="${t.key}">
            ${t.sections.map(s => `
              <label><input type="checkbox" data-sec="${esc(s.id)}" ${sel.has(s.id) ? "checked" : ""}>
              <span>${esc(s.label)}</span><span class="n">${s.count}</span></label>`).join("")}
          </div>
        </div>`;
    }).join("");

    const chip = (on, attrs, text) => `<button class="mx-chip${on ? " on" : ""}" ${attrs}>${text}</button>`;

    body.innerHTML = `
      ${presets.length ? `<div class="mx-label">Saved profiles</div>
      <div class="mx-chips" style="margin-bottom:4px">
        ${presets.map((p, i) => `<span class="mx-chip" data-preset="${i}" title="Load this profile">${esc(p.name)}
          <span class="x" data-del-preset="${i}" title="Delete">✕</span></span>`).join("")}
      </div>` : ""}

      <div class="mx-label">Topics</div>
      <div class="mx-topics">${topics}</div>
      <div class="mx-chips" style="margin-top:9px">
        ${chip(false, 'data-all="1"', "all")}
        ${chip(false, 'data-none="1"', "none")}
        ${chip(cfg.onlyMissed, 'data-missed="1"', `only the ones I missed (${nMissed})`)}
        ${chip(cfg.drills, 'data-drills="1"', "include typing drills")}
      </div>

      <div class="mx-label">How many</div>
      <div class="mx-chips">
        ${[10, 20, 40].map(n => chip(cfg.count === n, `data-count="${n}"`, n)).join("")}
        ${chip(cfg.count === 0, 'data-count="0"', "all")}
      </div>

      <div class="mx-label">Order</div>
      <div class="mx-chips">
        ${chip(cfg.order === "random", 'data-order="random"', "random")}
        ${chip(cfg.order === "topic", 'data-order="topic"', "grouped by topic")}
      </div>

      <div class="mx-label">Timer</div>
      <div class="mx-chips">
        ${chip(cfg.timer === 0, 'data-timer="0"', "no limit")}
        ${chip(cfg.timer === 60, 'data-timer="60"', "60 s")}
        ${chip(cfg.timer === 90, 'data-timer="90"', "90 s")}
        ${chip(cfg.timer === 120, 'data-timer="120"', "2 min")}
      </div>

      <div class="mx-label">This mix</div>
      <div class="mx-chips">
        <button class="mx-chip ghost" data-save="1">＋ save as profile</button>
      </div>`;

    // indeterminate checkboxes
    for (const t of BANK.topics) {
      const on = t.sections.filter(s => sel.has(s.id)).length;
      const cb = body.querySelector(`[data-topic-cb="${t.key}"]`);
      if (cb) cb.indeterminate = on > 0 && on < t.sections.length;
    }

    body.onclick = e => {
      const el = e.target.closest("[data-preset],[data-del-preset],[data-exp],[data-topic-lbl],[data-all],[data-none],[data-missed],[data-drills],[data-count],[data-order],[data-timer],[data-save]");
      if (!el) return;
      const d = el.dataset;
      if (d.delPreset !== undefined) { e.stopPropagation(); presets.splice(+d.delPreset, 1); save(K.presets, presets); renderModal(); return; }
      if (d.preset !== undefined) { applyPreset(presets[+d.preset]); return; }
      if (d.exp !== undefined || d.topicLbl !== undefined) {
        const key = d.exp !== undefined ? d.exp : d.topicLbl;
        body.querySelector(`[data-sub="${key}"]`).classList.toggle("open");
        body.querySelector(`.mx-topic[data-topic="${key}"]`).classList.toggle("expanded");
        return;
      }
      if (d.all) { cfg.sel = ALL_SECTIONS.slice(); }
      else if (d.none) { cfg.sel = []; }
      else if (d.missed) { cfg.onlyMissed = !cfg.onlyMissed; }
      else if (d.drills) { cfg.drills = !cfg.drills; }
      else if (d.count !== undefined) { cfg.count = +d.count; }
      else if (d.order) { cfg.order = d.order; }
      else if (d.timer !== undefined) { cfg.timer = +d.timer; }
      else if (d.save) { savePreset(); return; }
      persist(); renderModal();
    };

    body.onchange = e => {
      const cb = e.target;
      if (cb.dataset.sec !== undefined) {
        const s = new Set(cfg.sel);
        cb.checked ? s.add(cb.dataset.sec) : s.delete(cb.dataset.sec);
        cfg.sel = [...s];
      } else if (cb.dataset.topicCb !== undefined) {
        const t = BANK.topics.find(x => x.key === cb.dataset.topicCb);
        const s = new Set(cfg.sel);
        t.sections.forEach(x => cb.checked ? s.add(x.id) : s.delete(x.id));
        cfg.sel = [...s];
      } else return;
      persist(); renderModal();
    };

    const n = pool().length;
    const take = cfg.count === 0 ? n : Math.min(cfg.count, n);
    q$(".mx-tally", modal).innerHTML = n
      ? `<b>${take}</b> de ${n} preguntas disponibles`
      : `Ninguna pregunta con estos filtros`;
    q$("#mx-start", modal).disabled = !n;
  }

  function persist() { save(K.cfg, cfg); }

  function savePreset() {
    const name = prompt("Profile name (e.g. Backend + APIs):", "");
    if (!name) return;
    presets = presets.filter(p => p.name !== name.trim());
    presets.push({ name: name.trim(), cfg: JSON.parse(JSON.stringify(cfg)) });
    save(K.presets, presets);
    renderModal();
    toast("Perfil guardado");
  }

  function applyPreset(p) {
    if (!p) return;
    cfg = Object.assign(cfg, JSON.parse(JSON.stringify(p.cfg)));
    cfg.sel = cfg.sel.filter(id => ALL_SECTIONS.includes(id));
    persist(); renderModal();
    toast("Perfil «" + p.name + "» cargado");
  }

  /* ---------------- la tanda ---------------- */
  function start() {
    const p = pool();
    if (!p.length) return;
    let picked = shuffle(p);
    if (cfg.count > 0) picked = picked.slice(0, cfg.count);
    if (cfg.order === "topic") {
      const idx = new Map(QS.map((q, i) => [q.id, i]));
      picked.sort((a, b) => idx.get(a.id) - idx.get(b.id));
    }
    run.queue = picked; run.i = 0; run.res = {}; run.done = false; run.on = true;
    closeModal();
    document.body.classList.add("mix-on");
    q$("#crumb").innerHTML = "<b>🎲 mix › </b>" + picked.length + " questions";
    q$("#meta").textContent = cfg.timer ? cfg.timer + " s per question" : "no timer";
    renderCard();
  }

  // restore=false when the caller is about to open another document (avoids two stacked open() calls)
  function exitMix(restore = true) {
    if (!run.on) return;
    run.on = false; stopClock();
    document.body.classList.remove("mix-on");
    if (!restore) return;
    if (state.current) open(state.current);
    else {
      q$("#doc").innerHTML = WELCOME;
      mountWelcomeCta();
      q$("#crumb").textContent = "—"; q$("#meta").textContent = "";
      if (typeof buildToc === "function") buildToc();
    }
  }

  /* --- timer --- */
  function stopClock() { clearInterval(run.tick); run.tick = null; }
  function startClock() {
    stopClock();
    if (!cfg.timer) return;
    run.left = cfg.timer;
    paintClock();
    run.tick = setInterval(() => {
      run.left--;
      paintClock();
      if (run.left <= 0) { stopClock(); if (!run.shown) { reveal(); toast("⏱ Time is up"); } }
    }, 1000);
  }
  function paintClock() {
    const el = q$(".mx-clock");
    if (!el) return;
    const m = Math.floor(Math.max(0, run.left) / 60), s = Math.max(0, run.left) % 60;
    el.textContent = `⏱ ${m}:${String(s).padStart(2, "0")}`;
    el.classList.toggle("warn", run.left <= 15);
  }

  /* --- card --- */
  function renderCard() {
    const q = run.queue[run.i];
    run.shown = false;
    const pct = ((run.i) / run.queue.length) * 100;
    const doc = q$("#doc");
    doc.innerHTML = `
      <div class="mx-run">
        <div class="mx-head">
          <button class="mx-ghost" data-act="exit" title="Leave the mix (Esc)">← exit</button>
          <span class="mx-pos"><b>${run.i + 1}</b> / ${run.queue.length}</span>
          <span class="mx-bar"><i style="width:${pct}%"></i></span>
          ${cfg.timer ? `<span class="mx-clock">⏱</span>` : ""}
        </div>
        <div class="mx-tags">
          <span class="mx-tag">${q.icon} ${esc(q.topicLabel)}</span>
          <span class="mx-tag soft">${esc(q.section)}</span>
          ${q.kind === "drill" ? `<span class="mx-tag soft">typing drill</span>` : ""}
          ${missed[q.id] ? `<span class="mx-tag soft">missed ×${missed[q.id]}</span>` : ""}
        </div>
        <div class="mx-q">${q.q}</div>
        <div id="mx-slot"></div>
        <div class="mx-actions" id="mx-actions">
          <button class="mx-go" data-act="reveal">Show answer</button>
          <span class="sp"></span>
          ${run.i > 0 ? `<button class="mx-ghost" data-act="prev">←</button>` : ""}
          <button class="mx-ghost" data-act="skip">skip →</button>
        </div>
        <p class="mx-hint">
          <kbd>space</kbd> show / next &nbsp;·&nbsp;
          <kbd>1</kbd> missed &nbsp;·&nbsp; <kbd>2</kbd> knew it &nbsp;·&nbsp;
          <kbd>←</kbd> <kbd>→</kbd> navigate &nbsp;·&nbsp; <kbd>Esc</kbd> exit
        </p>
      </div>`;
    doc.querySelector(".mx-run").onclick = onCardClick;
    q$("#scroller").scrollTop = 0;
    startClock();
  }

  function onCardClick(e) {
    const el = e.target.closest("[data-act]");
    if (!el) return;
    const a = el.dataset.act;
    if (a === "exit") exitMix();
    else if (a === "reveal") reveal();
    else if (a === "skip") next();
    else if (a === "prev") prev();
    else if (a === "ok") grade(true);
    else if (a === "fail") grade(false);
    else if (a === "again") restartWith(run.queue.filter(q => run.res[q.id] === false));
    else if (a === "new") openModal();
    else if (a === "source") { e.preventDefault(); goSource(QS.find(x => x.id === el.dataset.id)); }
  }

  function reveal() {
    if (run.shown || run.done) return;
    run.shown = true;
    stopClock();
    const q = run.queue[run.i];
    q$("#mx-slot").innerHTML = `<div class="mx-a">${q.a}</div>
      <p class="mx-src">Source: <a href="#" data-act="source" data-id="${esc(q.id)}">${esc(q.path)}</a> · ${esc(q.num)}</p>`;
    q$("#mx-actions").innerHTML = `
      <button class="mx-fail" data-act="fail">✗ Missed <kbd>1</kbd></button>
      <button class="mx-ok" data-act="ok">✓ Knew it <kbd>2</kbd></button>
      <span class="sp"></span>
      ${run.i > 0 ? `<button class="mx-ghost" data-act="prev">←</button>` : ""}
      <button class="mx-ghost" data-act="skip">next →</button>`;
  }

  function grade(ok) {
    if (run.done) return;
    const q = run.queue[run.i];
    run.res[q.id] = ok;
    if (ok) delete missed[q.id];
    else missed[q.id] = (missed[q.id] || 0) + 1;
    save(K.missed, missed);
    next();
  }

  function next() {
    if (run.i >= run.queue.length - 1) return finish();
    run.i++; renderCard();
  }
  function prev() { if (run.i > 0) { run.i--; renderCard(); } }

  function goSource(q) {
    if (!q) return;
    exitMix(false);
    open(q.path).then(() => {
      const h = document.getElementById(q.slug);
      if (h && typeof scrollToHeading === "function") scrollToHeading(h);
    });
  }

  function restartWith(list) {
    if (!list.length) return;
    run.queue = list; run.i = 0; run.res = {}; run.done = false;
    q$("#crumb").innerHTML = "<b>🎲 mix › </b>" + list.length + " questions";
    renderCard();
  }

  function finish() {
    run.done = true; stopClock();
    const graded = run.queue.filter(q => run.res[q.id] !== undefined);
    const ok = graded.filter(q => run.res[q.id]).length;
    const bad = run.queue.filter(q => run.res[q.id] === false);
    const pctOk = graded.length ? Math.round((ok / graded.length) * 100) : 0;
    q$("#doc").innerHTML = `
      <div class="mx-run">
        <h2 style="margin-top:0">🎲 Mix finished</h2>
        <div class="mx-score">
          <div class="big">${ok}<small> / ${graded.length || 0} graded</small></div>
          <div class="big">${pctOk}<small>%</small></div>
        </div>
        ${bad.length ? `<div class="mx-label" style="margin-bottom:10px">The ones you missed</div>
        <ul class="mx-list">${bad.map(q => `
          <li class="bad"><span class="mk">✗</span><span class="tp">${esc(q.topic)}</span>
          <span style="flex:1">${q.q}<br><a href="#" data-act="source" data-id="${esc(q.id)}"
            style="font-size:11.5px">open in ${esc(q.path)}</a></span></li>`).join("")}</ul>` :
        `<p>You did not mark any as missed. ${graded.length ? "Raise the difficulty: less time, or more topics." : "Grade your answers (1 / 2) to keep a record."}</p>`}
        <div class="mx-actions">
          ${bad.length ? `<button class="mx-go" data-act="again">Retry the ${bad.length} missed</button>` : ""}
          <button class="mx-ghost" data-act="new">New mix</button>
          <button class="mx-ghost" data-act="exit">Back to the documents</button>
        </div>
      </div>`;
    q$("#doc .mx-run").onclick = onCardClick;
    q$("#scroller").scrollTop = 0;
  }

  /* ---------------- entry points ---------------- */
  const btn = document.createElement("button");
  btn.id = "mix-btn"; btn.className = "icon-btn";
  btn.title = "Mix questions by topic (m)";
  btn.innerHTML = "🎲 <span>Mix</span>";
  btn.onclick = openModal;
  const bar = q$("#topbar");
  if (bar) bar.insertBefore(btn, q$("#theme-btn"));

  addEventListener("keydown", e => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName);
    if (isOpen()) {
      if (e.key === "Escape") { closeModal(); e.stopPropagation(); e.preventDefault(); }
      else if (e.key === "Enter" && !typing) { start(); e.stopPropagation(); e.preventDefault(); }
      return;
    }
    if (!run.on) {
      if (e.key === "m" && !typing) { openModal(); e.stopPropagation(); e.preventDefault(); }
      return;
    }
    if (typing) return;
    const k = e.key;
    const swallow = () => { e.stopPropagation(); e.preventDefault(); };
    if (k === "Escape") { exitMix(); swallow(); }
    else if (k === " " || k === "Enter") { run.done ? null : (run.shown ? next() : reveal()); swallow(); }
    else if (k === "1" || k === "f") { if (run.shown) grade(false); swallow(); }
    else if (k === "2" || k === "d") { if (run.shown) grade(true); swallow(); }
    else if (k === "ArrowRight" || k === "n") { if (!run.done) next(); swallow(); }
    else if (k === "ArrowLeft" || k === "p") { if (!run.done) prev(); swallow(); }
    else if ("ajkcgG".includes(k)) swallow();   // the viewer shortcuts do not apply here
  }, true);

  // call to action on the welcome screen (remounted when returning from the mix)
  function mountWelcomeCta() {
    const wel = q$("#welcome");
    if (!wel || wel.querySelector("#mx-welcome")) return;
    const p = document.createElement("p");
    p.style.marginTop = "26px";
    p.innerHTML = `<button class="mx-go" id="mx-welcome">🎲 Build a question mix</button>
      <span style="margin-left:12px;font-size:12px;color:var(--fg-faint)">${QS.length} questions · ${BANK.topics.length} topics · press <kbd>m</kbd></span>`;
    wel.appendChild(p);
  }
  document.addEventListener("click", e => { if (e.target.closest("#mx-welcome")) openModal(); });
  mountWelcomeCta();
})();
