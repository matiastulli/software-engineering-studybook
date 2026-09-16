# ❓ Question Bank — how to use it

Interview questions with model answers, derived from everything in `theory/`.

**Answer out loud, in English.** The bottleneck is rarely knowing the answer; it's saying it
fluently under pressure. Reading the answer out loud is half the exercise.

---

## How to study with this

**Answers are collapsed.** Read the question and answer it **out loud and in full** before
opening it. If you peek without trying, you aren't studying — you're reading.

In the viewer:
- Click any question to open its answer.
- <kbd>a</kbd> — open / close **every** answer in the document.
- <kbd>j</kbd> / <kbd>k</kbd> — next / previous document.
- <kbd>m</kbd> — **mix mode**: shuffles questions from the topics you pick.

---

## 🎲 Mix mode — one run per interview

Every interview asks about a different stack. The **🎲 Mix** button in the viewer (or the
<kbd>m</kbd> key) builds a run from the topics you check, shuffled — exactly what happens in a
real interview, where nobody warns you that it's Airflow's turn now.

**How to use it**

1. Check the topics — or open a topic's ▶ and check only some sections (from dbt, say, only
   *Incremental models*).
2. Pick how many (10 / 20 / 40 / all), the order, and whether you want a timer (60 s, 90 s or
   2 min per question; when it runs out, the answer reveals itself).
3. **Start**. Answer out loud, reveal with <kbd>space</kbd>, and grade yourself:
   <kbd>1</kbd> missed, <kbd>2</kbd> knew it.

At the end you get your score, the list of the ones you missed with a link back to the source
document, and a button to **retry just those**.

**Profiles.** Save a selection under a name (*«Backend + APIs»*, *«SQL and warehousing»*) and
load it with one click next time. Missed questions are recorded: the **«only the ones I missed»**
filter builds a run from those, even across different topics.

| Key | What it does |
| --- | --- |
| <kbd>m</kbd> | Open the mix |
| <kbd>space</kbd> | Show answer / next |
| <kbd>1</kbd> / <kbd>2</kbd> | Missed / knew it |
| <kbd>←</kbd> <kbd>→</kbd> | Navigate without grading |
| <kbd>Esc</kbd> | Leave the mix |

### The three-pass protocol

| Pass | What you do | Goal |
| --- | --- | --- |
| **1 · Recognize** | Open the answers and read everything | Map what exists and what you didn't know |
| **2 · Retrieve** | Cover the answer, respond out loud, then compare | Active recall — this is where learning happens |
| **3 · Time it** | 90 seconds per answer, out loud, no pauses | Fluency under pressure |

Mark the ones you missed and go back only to those. Reviewing what you already know feels
productive and isn't.

---

## The files

| File | Questions about |
| --- | --- |
| [system-design-questions.md](system-design-questions.md) | The method, sizing, hot/cold, the six cases in this repo |
| [snowflake-questions.md](snowflake-questions.md) | Query profile, pruning, spilling, clustering, sizing, cost |
| [dbt-questions.md](dbt-questions.md) | Materializations, incremental, snapshots, tests, contracts |
| [airflow-questions.md](airflow-questions.md) | Idempotency, Assets (formerly Datasets), backfills, DAG refactors, Airflow 3 changes |
| [sql-questions.md](sql-questions.md) | Window functions, dedup, joins, grain, performance |
| [python-questions.md](python-questions.md) | Data structures, generators, concurrency, and typing drills |
| [streaming-questions.md](streaming-questions.md) | Kafka/Kinesis/SQS, delivery semantics, event time |
| [databases-caching-questions.md](databases-caching-questions.md) | SQL vs NoSQL, Redis, consistency, CDC |
| [ownership-troubleshooting-questions.md](ownership-troubleshooting-questions.md) | Production, incidents, decisions, scoping with customers, and phrasing |
| [llm-questions.md](llm-questions.md) | LLM agents: system prompt, guardrails, hallucinations, evals and regressions, voice latency |

Answers assume current versions (Airflow 3, dbt 1.9+, Kafka 4.x). Where something changed
recently, the answer says so — confidently quoting the old version costs you points. PySpark and
Databricks don't have their own bank yet; for now study them from
[pyspark.md](../data-engineering/pyspark.md) and [databricks.md](../data-engineering/databricks.md).

---

## The ten that come up most

If you have ten minutes before an interview, practice these:

1. *"Walk me through how you'd design X."* → sizing first, always. See [system-design-questions.md](system-design-questions.md).
2. *"How do you know that number is right?"* → structural tests + reconciliation against the GL.
3. *"A query got slow. Debug it."* → pruning → spilling → join explosion.
4. *"Why not Spark / Kafka / Flink here?"* → because the volume doesn't justify it — and say the number.
5. *"How do you handle late-arriving data?"* → lookback window + idempotent merge.
6. *"What's the difference between at-least-once and exactly-once?"* → and why "effectively-once" is the honest answer.
7. *"How would you cut our Snowflake bill?"* → auto-suspend, warehouses per workload, then tuning.
8. *"Tell me about a production incident you owned."* → STAR, with numbers.
9. *"How do you refactor something people depend on?"* → strangler: build alongside, prove it, migrate, delete.
10. *"Where would you push back on this design?"* → having an opinion *is* the answer.
