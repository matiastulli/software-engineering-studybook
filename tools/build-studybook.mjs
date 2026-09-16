// Regenera index.html a partir de cada .md de theory/.
// Reusa el shell (CSS + app JS) de tools/shell.html y le cambia el payload __DOCS__,
// agregando Mermaid offline y el modo mix (tools/mix.{css,js}).
//   node tools/build-studybook.mjs        (deps vendored in tools/, no npm install)

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import { Marked } from "./marked.esm.js";

// Repo root, resolved from this file's location so the build works on any machine.
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..");
const THEORY = path.join(ROOT, "theory");
const SHELL = path.join(HERE, "shell.html");
const OUT = path.join(ROOT, "index.html");
const MERMAID = fs.readFileSync(path.join(ROOT, "tools", "mermaid.min.js"), "utf8");
const MIX_CSS = fs.readFileSync(path.join(ROOT, "tools", "mix.css"), "utf8");
const MIX_JS  = fs.readFileSync(path.join(ROOT, "tools", "mix.js"), "utf8");
const ADV_CSS = fs.readFileSync(path.join(ROOT, "tools", "advisor.css"), "utf8");
const ADV_JS  = fs.readFileSync(path.join(ROOT, "tools", "advisor.js"), "utf8");

/* ---------- markdown -> html ---------- */
const esc = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
                  .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

/* A JS string literal holding the JSON for `value`, safe to inline in a <script>.
   The `</` escape stops any payload containing "</script>" from closing the tag early. */
const jsString = value => JSON.stringify(JSON.stringify(value)).replace(/<\//g, "<\\/");

const seen = new Map();
function slug(text) {
  let s = text.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^\w\s-]/g, "").trim().replace(/\s+/g, "-").replace(/-+/g, "-");
  if (!s) s = "section";
  const n = (seen.get(s) || 0) + 1;
  seen.set(s, n);
  return n === 1 ? s : `${s}-${n}`;
}

const marked = new Marked({ gfm: true, breaks: false });
marked.use({
  renderer: {
    code({ text, lang }) {
      if ((lang || "").trim().toLowerCase() === "mermaid")
        return `<pre class="mermaid">${esc(text)}</pre>\n`;
      const cls = lang ? ` class="language-${esc(lang.split(/\s+/)[0])}"` : "";
      return `<pre><code${cls}>${esc(text)}</code></pre>\n`;
    },
    heading({ tokens, depth }) {
      const inner = this.parser.parseInline(tokens);
      const plain = inner.replace(/<[^>]+>/g, "");
      return `<h${depth} id="${slug(plain)}">${inner}</h${depth}>\n`;
    }
  }
});

/* ---------- last-commit times ---------- */
// The embedded mtime only drives live-reload change detection, which is inert in the static
// export. Taking it from git instead of the filesystem keeps the build reproducible: a fresh
// clone has checkout mtimes, so stat() would make every clone emit a different index.html.
function commitTimes() {
  const map = new Map();
  try {
    const out = execFileSync("git", ["log", "--format=C%ct", "--name-only", "--no-renames", "--", "theory"],
                             { cwd: ROOT, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
    let t = 0;
    for (const line of out.split("\n")) {
      if (line.startsWith("C")) t = Number(line.slice(1)) || 0;
      else if (line && !map.has(line)) map.set(line, t);   // newest commit wins
    }
  } catch { /* no git, or not a repo: fall back to filesystem mtime */ }
  return map;
}
const COMMITTED = commitTimes();

/* ---------- collect ---------- */
function walk(dir, acc = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, acc);
    else if (/\.(md|py)$/.test(e.name)) acc.push(p);
  }
  return acc;
}

// group key -> label, in display order
const GROUPS = [
  ["questions",          "❓ Questions & Answers"],
  ["system_design",      "🏗️  System Design — Cases"],
  ["system_design/99-reference", "📚 System Design — Reference"],
  ["cloud",              "☁️  Cloud & Architecture"],
  ["software-design",    "🧩 Software Design"],
  ["data-engineering",   "🗄️  Data Engineering"],
  ["backend",            "🐍 Backend & APIs"],
  ["frontend",           "🌐 Frontend"],
  ["ai",                 "🤖 AI & LLMs"],
  [".",                  "★ General"]
];
const label = k => (GROUPS.find(g => g[0] === k) || [k, k])[1];

function groupKeyFor(rel) {
  const dir = path.dirname(rel);
  if (dir === ".") return ".";
  if (rel.startsWith("system_design/99-reference/")) return "system_design/99-reference";
  if (rel.startsWith("system_design/")) return "system_design";
  return dir.split("/")[0];
}

function titleFor(rel, src) {
  const h1 = src.match(/^#\s+(.+?)\s*$/m);
  if (h1) return h1[1].replace(/[*`_]/g, "").trim();
  return path.basename(rel).replace(/\.(md|py)$/, "").replace(/[-_]/g, " ");
}

const files = walk(THEORY);
const docs = {};
const byGroup = new Map();

for (const abs of files) {
  const rel = path.relative(THEORY, abs).split(path.sep).join("/");
  const raw = fs.readFileSync(abs, "utf8");
  const stat = fs.statSync(abs);
  const isPy = rel.endsWith(".py");
  const pretty = path.basename(rel).replace(/\.py$/, "").replace(/[-_]/g, " ")
                     .replace(/\b\w/g, c => c.toUpperCase()) + " (Python)";
  const src = isPy ? "# " + pretty + "\n\n```python\n" + raw + "\n```\n" : raw;

  seen.clear();
  const html = marked.parse(src);
  const words = raw.split(/\s+/).filter(Boolean).length;
  const lines = raw.split("\n").length;
  const gk = groupKeyFor(rel);

  const meta = { path: rel, file: path.basename(rel), title: titleFor(rel, src), group: gk,
                 lines, words, mtime: COMMITTED.get("theory/" + rel) ?? Math.floor(stat.mtimeMs / 1000) };
  docs[rel] = { ...meta, html, minutes: Math.max(1, Math.round(words / 220)) };
  delete docs[rel].group;
  if (!byGroup.has(gk)) byGroup.set(gk, []);
  byGroup.get(gk).push(meta);
}

// Deterministic order inside a group: the index first, then the reading order of the
// cases (every case file is literally named README.md, so sort on path, not on file).
const CASE_ORDER = [
  "questions/README.md",
  "system_design/README.md",
  "system_design/truck-stream-processor/README.md",
  "system_design/live-load-board/README.md",
  "system_design/cdc-postgres-to-warehouse/README.md",
  "system_design/document-ingestion-pipeline/README.md",
  "system_design/freight-billing-warehouse/README.md",
  "system_design/warehouse-refactor-consolidation/README.md"
];
const rank = f => {
  const i = CASE_ORDER.indexOf(f.path);
  if (i >= 0) return i;
  return f.file.toLowerCase().startsWith("readme") ? -1 : 50;
};
const order = k => GROUPS.findIndex(g => g[0] === k);
const groups = [...byGroup.entries()]
  .sort((a, b) => (order(a[0]) < 0 ? 99 : order(a[0])) - (order(b[0]) < 0 ? 99 : order(b[0])))
  .map(([key, fl]) => ({
    key, label: label(key),
    files: fl.sort((a, b) => rank(a) - rank(b) || a.path.localeCompare(b.path))
  }));

const tree = { root: "theory/", total: Object.keys(docs).length, groups };
console.error(`${tree.total} docs across ${groups.length} groups`);
for (const g of groups) console.error(`  ${g.key.padEnd(28)} ${g.files.length}`);

/* ---------- question bank (mix mode) ---------- */
// Each questions/<topic>-questions.md contributes a topic; each <h2> a section and each
// <details><summary><b>Qn.</b> …</summary> a question with its answer.
const TOPIC_ICONS = {
  "system-design": "🏗️", snowflake: "❄️", dbt: "🔧", airflow: "🌀", sql: "🗄️",
  python: "🐍", streaming: "📡", "databases-caching": "💾", llm: "🤖", "ownership-troubleshooting": "🧭"
};
const TOPIC_ORDER = ["system-design", "snowflake", "dbt", "airflow", "sql",
                     "python", "streaming", "databases-caching", "llm", "ownership-troubleshooting"];

const unesc = s => s.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"')
                    .replace(/&#39;/g, "'").replace(/&amp;/g, "&");
const stripTags = h => unesc(h.replace(/<[^>]+>/g, "")).replace(/\s+/g, " ").trim();

function extractBank() {
  const topics = [], questions = [];
  const paths = Object.keys(docs)
    .filter(p => /^questions\/.+-questions\.md$/.test(p))
    .sort((a, b) => {
      const k = p => TOPIC_ORDER.indexOf(path.basename(p).replace("-questions.md", ""));
      return (k(a) < 0 ? 99 : k(a)) - (k(b) < 0 ? 99 : k(b));
    });

  for (const rel of paths) {
    const key = path.basename(rel).replace("-questions.md", "");
    const label = docs[rel].title.split(/\s+—\s+/)[0].trim();
    const icon = TOPIC_ICONS[key] || "❓";
    const sections = [];
    let section = null;

    const re = /<h2 id="([^"]+)">([\s\S]*?)<\/h2>|<details><summary>([\s\S]*?)<\/summary>([\s\S]*?)<\/details>/g;
    let m;
    while ((m = re.exec(docs[rel].html))) {
      if (m[1] !== undefined) {
        section = { id: `${key}::${m[1]}`, slug: m[1], label: stripTags(m[2]), count: 0 };
        sections.push(section);
        continue;
      }
      if (!section) {   // questions before the first <h2>
        section = { id: `${key}::general`, slug: "", label: "General", count: 0 };
        sections.push(section);
      }
      const summary = m[3];
      const numMatch = summary.match(/^\s*<b>([^<]+)<\/b>\s*/);
      const num = numMatch ? numMatch[1].replace(/\.$/, "").trim() : `Q${questions.length + 1}`;
      const q = (numMatch ? summary.slice(numMatch[0].length) : summary).trim();
      questions.push({
        id: `${key}#${num}`, topic: key, topicLabel: label, icon,
        section: section.label, sectionId: section.id, slug: section.slug,
        num, kind: /^D/.test(num) ? "drill" : "q",
        q, a: m[4].trim(), path: rel
      });
      section.count++;
    }

    const used = sections.filter(s => s.count > 0);
    if (used.length) {
      topics.push({ key, label, icon, path: rel, sections: used,
                    count: used.reduce((n, s) => n + s.count, 0) });
    }
  }
  return { topics, questions };
}

const bank = extractBank();
console.error(`\nquestion bank: ${bank.questions.length} questions across ${bank.topics.length} topics`);
for (const t of bank.topics) console.error(`  ${t.key.padEnd(28)} ${String(t.count).padStart(3)}  (${t.sections.length} sections)`);

/* ---------- assemble from the existing shell ---------- */
let shell = fs.readFileSync(SHELL, "utf8");
const i = shell.indexOf("window.__DOCS__ = ");
const after = shell.indexOf(";</script>", i);
let head = shell.slice(0, i);
let tail = shell.slice(after);

// rebrand
head = head.replace('<html lang="es" data-theme="dark">', '<html lang="en" data-theme="dark">')
           .replace("<title>Technical Prep Guide — study material</title>",
                    "<title>Theory — study material</title>")
           .replace("<text y='.9em' font-size='90'>📘</text>", "<text y='.9em' font-size='90'>🏗️</text>")
           .replace("<h1>Technical Prep Guide</h1>", "<h1>Theory</h1>")
           .replace(/Static copy generated [^<·]*·\s*36 documents ·/,
                    `Static copy of <code>theory/</code> · ${tree.total} documents ·`)
           .replace("<h2>📘 Your notes, in one place</h2>",
                    "<h2>🏗️ Theory</h2>")
           .replace("Pick a document on the left. Anything you add or change in this folder shows up on its own, with nothing to restart.",
                    "A question bank, system design cases with diagrams, and the theory behind SQL, backend, frontend and cloud. Links between documents work: click one and you navigate.");

head = head.replace("<kbd>c</kbd> collapse sections",
                    "<kbd>a</kbd> show / hide answers &nbsp;·&nbsp;\n            <kbd>m</kbd> question mix &nbsp;·&nbsp;\n            <kbd>r</kbd> advisor (needs → architecture) &nbsp;·&nbsp;\n            <kbd>c</kbd> collapse sections");

tail = tail.replace('document.title = data.title + " · Technical Prep Guide";',
                    'document.title = data.title + " · Theory";');

// mermaid hooks
// NB: match the newline as \r?\n — the shell has been LF and CRLF at different times.
// The calls are guarded: the bundle is loaded after this script, so on the very first
// document renderMermaid may not exist yet and a bare call would reject the async open.
const MERMAID_CALL = 'if (typeof renderMermaid === "function") renderMermaid();';
tail = tail.replace(/(  typesetMath\(\);)(\r?\n)/, (m, call, nl) => `${call}${nl}  ${MERMAID_CALL}${nl}`);
tail = tail.replace('  try { localStorage.setItem("ip-theme", theme); } catch {}',
                    '  try { localStorage.setItem("ip-theme", theme); } catch {}\n  ' + MERMAID_CALL);

const mermaidCss = `
/* ---------- mermaid diagrams ---------- */
#doc pre.mermaid{
  background:var(--panel); border:1px solid var(--line); border-radius:12px;
  padding:18px; margin:22px 0; text-align:center; overflow-x:auto;
  font:13px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace; color:var(--fg-dim);
}
#doc pre.mermaid[data-processed]{ color:transparent; font-size:0; }
#doc pre.mermaid svg{ max-width:100%; height:auto; font-size:14px; }

/* ---------- collapsible questions ---------- */
#doc details{
  border:1px solid var(--line); border-radius:10px; background:var(--panel);
  margin:10px 0; overflow:hidden; transition:border-color .16s var(--ease);
}
#doc details:hover{ border-color:var(--scroll-hover) }
#doc details[open]{ background:var(--panel-2); border-color:var(--accent) }
#doc details > summary{
  cursor:pointer; padding:13px 16px 13px 40px; position:relative;
  list-style:none; font-weight:500; color:var(--fg);
}
#doc details > summary::-webkit-details-marker{ display:none }
#doc details > summary::before{
  content:"›"; position:absolute; left:17px; top:50%;
  transform:translateY(-50%); color:var(--accent); font-size:17px;
  transition:transform .18s var(--ease-out); display:inline-block;
}
#doc details[open] > summary::before{ transform:translateY(-50%) rotate(90deg) }
#doc details > summary b{ color:var(--accent-3); margin-right:6px; font-weight:700 }
#doc details > summary:hover{ color:var(--accent) }
#doc details > *:not(summary){ padding-left:16px; padding-right:16px }
#doc details > *:not(summary):last-child{ padding-bottom:6px }
#doc details pre{ margin-left:0; margin-right:0 }
${MIX_CSS}
${ADV_CSS}
</style>`;
head = head.replace(/<\/style>/, () => mermaidCss);   // fn replacer: no $& expansion

// Script order matters. The question bank, mix and advisor come FIRST so their buttons and
// shortcuts are live immediately; the 2.5 MB Mermaid bundle is parsed last, since nothing
// needs it until a document containing a diagram is opened.
const mermaidJs = `
<script>window.__BANK__ = JSON.parse(${jsString(bank)});<\/script>
<script>${MIX_JS}<\/script>
<script>${ADV_JS}<\/script>
<script>${MERMAID}<\/script>
<script>
function toggleAllAnswers(force){
  const items = [...document.querySelectorAll("#doc details")];
  if (!items.length) return false;
  const open = force !== undefined ? force : !items.every(d => d.open);
  items.forEach(d => { d.open = open; });
  return true;
}
document.addEventListener("keydown", e => {
  if (e.key !== "a" || e.metaKey || e.ctrlKey || e.altKey) return;
  const el = document.activeElement;
  if (el && /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName)) return;  // do not steal the search box
  if (toggleAllAnswers()) e.preventDefault();
});

async function renderMermaid(){
  if (typeof mermaid === "undefined") return;
  const nodes = [...document.querySelectorAll("#doc pre.mermaid")];
  if (!nodes.length) return;
  const dark = document.documentElement.dataset.theme !== "light";
  mermaid.initialize({
    startOnLoad:false, securityLevel:"loose",
    theme: dark ? "dark" : "default",
    themeVariables: dark
      ? { background:"#141924", primaryColor:"#1b2230", primaryTextColor:"#e4e9f2",
          primaryBorderColor:"#3d4a5e", lineColor:"#7ea2ff", secondaryColor:"#1e2836",
          tertiaryColor:"#151c27", fontSize:"14px" }
      : { background:"#ffffff", primaryColor:"#f1f4f9", primaryTextColor:"#151a22",
          primaryBorderColor:"#c2cddb", lineColor:"#3558d6", secondaryColor:"#eaf0f8",
          tertiaryColor:"#f8fafc", fontSize:"14px" },
    flowchart:{ curve:"basis", htmlLabels:true, useMaxWidth:true }
  });
  for (const n of nodes){
    if (n.dataset.src) { n.innerHTML = n.dataset.src; n.removeAttribute("data-processed"); }
    else n.dataset.src = n.innerHTML;
  }
  // Awaited: each diagram becomes an SVG that is far taller than its source text, so the
  // cached heading offsets are stale until it settles — the TOC would track the wrong section.
  try { await mermaid.run({ nodes }); } catch(e) { console.warn("mermaid:", e); }
  if (typeof measureHeadings === "function") { measureHeadings(); onScrollShell(true); }
}
// The bundle parses after the first document is already on screen; render it now.
renderMermaid();
<\/script>
</body>`;
tail = tail.replace("</body>", () => mermaidJs);       // fn replacer: no $& expansion

// JSON.parse on a string literal beats a bare object literal for a payload this size:
// the JSON grammar is simpler, so engines parse it several times faster.
const out = head + "window.__DOCS__ = JSON.parse(" + jsString({ tree, docs }) + ")" + tail;
fs.writeFileSync(OUT, out);
console.error(`\nwrote ${path.relative(ROOT, OUT)}  (${(out.length/1048576).toFixed(2)} MB)`);
