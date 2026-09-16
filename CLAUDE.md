# Software Engineering Studybook

A self-contained, offline study app: senior backend / data-engineering / system-design notes,
6 worked system design cases and a 198-question drill bank, compiled into one searchable
`index.html` with no build step, no dependencies and no server.

Read `README.md` first — it explains the product (what studying with this looks like) in more
depth than this file does. This file is about how to work in the repo.

## The one rule that matters

**Content lives in `theory/**/*.md` (and `.py` under `practical/`). `index.html` is a build
artifact.** Never hand-edit `index.html`. Edit the source Markdown, then rebuild:

```bash
node tools/build-studybook.mjs      # theory/**/*.{md,py} -> index.html
```

No `npm install` — `marked` and `mermaid` are vendored under `tools/`, so the build is one file
read and one file write. `index.html` is committed (not built in CI) so the repo stays
clone-and-open; always run the build and let it regenerate `index.html` after touching anything
under `theory/`, then `git status` to confirm only the files you meant to touch changed.

## Doc shape — don't deviate without a reason

Every file in `theory/` follows the same shape, and it's load-bearing (the builder parses
`<details>` blocks into the question bank — see below):

**TL;DR** (3–5 quotable lines) → **the problem** with real numbers → **the mechanism** →
**decide** ("pick X when \_\_\_, switch to Y when \_\_\_") → **failure modes** → **self-check**
questions with hidden answers.

The bet: rereading doesn't teach, retrieval does. Self-check questions use
`<details><summary><b>Qn.</b> question</summary>answer</details>` — that exact shape is what
`tools/build-studybook.mjs` scans for when building `theory/questions/*.md`'s mix-mode bank
(mix mode itself only draws from `theory/questions/`, not from every doc's self-check).

**Write for humans, not for robots.** Full sentences, not bullet-fragment soup. Explain a term
the first time it appears instead of assuming the reader already knows it. Tables and code
blocks are for content that's genuinely tabular/literal, not a way to avoid writing a sentence.
See `theory/ai/llm-prompting-and-evals.md` for the level of plain-English explanation to aim for.

## Repo layout

| Path | What it is |
|---|---|
| `theory/<topic>/*.md` | The actual content, grouped by folder (`ai`, `backend`, `cloud`, `data-engineering`, `frontend`, `software-design`, `system_design`) |
| `theory/questions/*.md` | The 198-question drill bank that powers mix mode — one topic per file |
| `theory/README.md` | Index of every theory doc with a one-line description — update it when you add/rename/retitle a doc |
| `practical/` | Hands-on drills (Python, SQL, Snowflake, PySpark, typing drills) — not part of the `index.html` build |
| `tools/build-studybook.mjs` | The builder: walks `theory/`, renders Mermaid, extracts questions, injects into `tools/shell.html` |
| `tools/shell.html` | Page chrome/template only — no content. Edit it to restyle the studybook, not to add content |
| `tools/*.css`, `tools/*.js` | Styling and behavior for the compiled page (search, mix mode, advisor, diagram zoom) — vendored deps (`marked.esm.js`, `mermaid.min.js`) live here too, don't touch them |
| `index.html` | Build output. Never hand-edit |

## When you add or change a doc

1. Match the doc shape above. Check a neighboring file in the same folder for tone and structure
   before writing.
2. If it's new, add it to the table in `theory/README.md` (and the folder list in `README.md`'s
   root table if the folder itself is new).
3. Mermaid diagrams use ` ```mermaid ` fences — the builder renders them inline.
4. Run `node tools/build-studybook.mjs` and check its summary output (doc counts per group,
   question counts per topic) look right before considering the change done.
5. `*.visual-check.*` files (diagram QA screenshots/reports) are gitignored — don't commit them,
   they're regenerated.

## Two subagents already exist here

- `staff-engineer-teacher` — turns `theory/`/`practical/` material into interactive study pages.
  Use it when the ask is "make a study page / lesson / visual explainer for X", not for editing
  the theory docs themselves.
- `frontend-developer` — for React/frontend work referencing the (external) reference dashboard
  project mentioned in worked examples.

The `/teacher` skill drives spaced-repetition quizzing and writes personal progress to
`.study-progress.md`, which is gitignored — never commit it.

## Things to not do

- Don't add a build step, bundler, framework or `npm install` dependency. The whole point is
  clone-and-open with zero setup.
- Don't invent a new doc shape or put content in `tools/shell.html`.
- Don't edit `index.html` directly — it will be silently overwritten by the next build.
- Don't touch vendored files (`tools/marked.esm.js`, `tools/mermaid.min.js`) except to bump the
  vendored version deliberately.
