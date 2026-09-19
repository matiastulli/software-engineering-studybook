# Software Engineering Studybook

A self-contained, offline study app for senior backend, data engineering and system design
topics — 38 notes, 6 worked system design cases and a 198-question drill bank, compiled into a
single searchable HTML page with no build step, no dependencies and no server.

**→ [Open the studybook](index.html)** (or [view it live](https://matiastulli.github.io/software-engineering-studybook/))

Clone it and double-click `index.html`. That's the whole setup. Everything — styles, search
index, Mermaid renderer, question bank — is inlined into the file, so it works on a plane.

---

## What `index.html` gives you

All 38 theory docs in one page, grouped by folder and searchable, with Mermaid diagrams rendered
inline. Press <kbd>m</kbd> for **mix mode**: pick the topics you expect to be asked about, and it
shuffles a run from the 198-question bank — timed if you want, graded as you go, with the ones you
missed saved so you can retry just those.

Keys: <kbd>/</kbd> search · <kbd>a</kbd> show/hide answers · <kbd>m</kbd> question mix ·
<kbd>r</kbd> advisor (needs → architecture) · <kbd>j</kbd> <kbd>k</kbd> next/previous doc.

## How the material is organized

Docs follow one shape, never padded: **TL;DR** (3–5 quotable lines) → **the problem** with real
numbers → **the mechanism** → **decide** ("pick X when \_\_\_, switch to Y when \_\_\_") →
**failure modes** → **self-check** questions with hidden answers.

The bet behind the format: rereading doesn't teach, retrieval does. Read a doc once, close it,
answer its self-check out loud.

| Folder | What lives there |
| --- | --- |
| `theory/system_design/` | The design method plus 6 worked cases — a truck telemetry stream processor, an in-memory load board, Postgres→warehouse CDC, an LLM document-ingestion pipeline, a freight billing warehouse, and a "you inherited a 400-model dbt project" refactor. Each sized, drawn and justified end to end. |
| `theory/data-engineering/` | SQL, PySpark, Snowflake performance & cost, Databricks |
| `theory/backend/` | Python, graph algorithms, Node/Express, REST APIs & webhooks, web performance & security |
| `theory/cloud/` | The core toolkit on AWS (one default service per job), a 10 / 10k / 100k scale ladder, the AWS services in each case, and a glossary of data services |
| `theory/software-design/` | Design patterns and architecture styles, kept to the set that actually gets asked |
| `theory/ai/` | Prompting a coding agent in a live interview, and building LLM agents: guardrails, evals |
| `theory/frontend/` | React and web vocabulary for engineers whose home turf isn't the frontend |
| `theory/behavioral/` | The STAR method for "tell me about a time..." questions, with a worked example and a story bank to prepare |
| `theory/questions/` | The 198-question bank with model answers, which powers mix mode |
| `practical/` | Hands-on drills: 25 Python exercises, SQL and Snowflake scripts, a PySpark set, and typing drills for rebuilding fluency under time pressure |
| `tools/` | The builder and its vendored dependencies |

Worked examples reference two projects kept outside this repo: a **reference API**
(Express/TypeScript) and a **reference dashboard** (Vite + React).

## Rebuilding

```bash
node tools/build-studybook.mjs      # theory/**/*.{md,py} -> index.html
```

No `npm install`. `marked` and `mermaid` are vendored in `tools/`, so the build is one file
read and one file write. Edit any Markdown under `theory/`, re-run, refresh the page.

The builder walks `theory/` for `.md` and `.py` files, groups them by folder, renders
` ```mermaid ` blocks into live diagrams, extracts `<details>` blocks into the mix-mode question
bank, and injects the whole payload into the `tools/shell.html` template.

## Notes

- Everything is in English — interface, notes and question bank.
- `tools/shell.html` is the page template (chrome only, no content); the builder fills its
  `__DOCS__` payload. Edit it to restyle the studybook.
- Diagram QA byproducts (`*.visual-check.*`) are gitignored — they're regenerated, not authored.
- `index.html` is committed rather than built in CI, so the repo stays clone-and-open.
