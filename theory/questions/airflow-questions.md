# Airflow — Questions

Answers assume **Airflow 3** (released April 2025) and flag where Airflow 2 behaves differently, because many companies still run 2.x.

---

## Core concepts

<details><summary><b>Q1.</b> What is Airflow for, and what is it not for?</summary>

**A.** Airflow is an orchestrator, not a compute engine. It schedules work, expresses dependencies, retries, backfills and alerts, and every task should be "tell something else to do the work, wait, check the result".

Pulling 2 GB through a `PythonOperator` is the classic anti-pattern: workers are small and shared, and their memory is not where data should live. Push the work to Snowflake or Spark and let Airflow coordinate.
</details>

<details><summary><b>Q2.</b> What's the single most common Airflow bug?</summary>

**A.** Using `datetime.now()` instead of the run's window. The task stops being idempotent, so a retry or a backfill produces a different result from the original run and nobody can reproduce anything.

Key everything on `data_interval_start` / `data_interval_end`, so a task gives the same output on schedule, on retry, or in a backfill six months later.

**Airflow 3 gotcha:** a plain cron string now resolves to `CronTriggerTimetable`, where `data_interval_start == data_interval_end` (the trigger time). For windowed ingests, use an explicit interval timetable (`CronDataIntervalTimetable`) or set `create_cron_data_intervals = True`. Otherwise your "window" is zero-width and the extract reads nothing.
</details>

<details><summary><b>Q3.</b> What are Assets (formerly Datasets) and what do they replace?</summary>

**A.** They schedule a DAG on data landing instead of on the clock. A producing task declares `outlets=[Asset("snowflake://RAW/shipments")]`, and a consuming DAG uses `schedule=[that_asset]`, so it runs when its inputs actually land. Airflow 2.4+ calls them Datasets; Airflow 3 renamed them Assets and added the `@asset` decorator.

They replace `ExternalTaskSensor`, which waits until timeout when the two DAGs' schedules or logical dates don't line up. They also replace the worse habit of guessing: "the load usually finishes by 3am, so I'll start the transform at 3:30".
</details>

<details><summary><b>Q4.</b> What is dynamic task mapping and when is it the right tool?</summary>

**A.** `extract.expand(carrier=CARRIERS)` creates one task per element at runtime. Use it when you have N independent units of the same work, like twelve carrier SFTP feeds.

A broken feed at carrier 7 fails one task, retries on its own and never blocks the other eleven. With a loop inside a single task, one bad carrier fails everything and the retry re-pulls all twelve. The trade-off: thousands of mapped tasks load the scheduler and metadata DB, so batch tiny units instead of mapping one task per row.
</details>

<details><summary><b>Q5.</b> Deferrable operators: what problem do they solve?</summary>

**A.** They stop sensors from wasting worker slots while they wait. A classic poke-mode sensor holds a worker slot while it sleeps, so twenty sensors waiting on files can occupy your entire pool doing nothing.

A deferrable operator hands the wait to the **triggerer** process and **releases the slot**, resuming when the condition is met. Use one for any sensor that might wait more than a few minutes. `mode="reschedule"` is the older middle ground: it frees the slot between pokes, but it still costs a scheduler round-trip for each poke.
</details>

---

## Design

<details><summary><b>Q6.</b> How do you decide DAG granularity?</summary>

**A.** One DAG per source domain, plus a transform DAG triggered by Assets.

A failing carrier SFTP shouldn't block the Stripe load, and small DAGs can be backfilled independently. The shape you're avoiding is the monolithic "everything nightly" DAG that fails at step 40 of 200 and gets restarted from the top by hand.
</details>

<details><summary><b>Q7.</b> How do you integrate dbt with Airflow?</summary>

**A.** Use **Cosmos**, which renders each dbt model as an Airflow task, so you get model-level retries and real lineage in the UI.

The alternative is one `BashOperator` running `dbt build`. It fails at model 300 of 400 after 40 minutes with no indication where, and the retry redoes all 300.

Pick Cosmos when the project is large and failures need to be localised. Pick a single `dbt build` task when the project is small and fast. Trade-off: Cosmos adds parse-time cost on big projects, so load from a pre-built `manifest.json` rather than running `dbt ls` on every parse.
</details>

<details><summary><b>Q8.</b> How do you stop a backfill from taking down the warehouse?</summary>

**A.** Cap the concurrency at three levels and give the backfill its own compute:
- `max_active_runs=1` for ordered replay.
- **Pools** capping how many tasks hit Snowflake at once.
- A dedicated backfill warehouse with a resource monitor.

An uncapped catchup over a year of daily runs launches hundreds of runs, which is how people get a five-figure surprise bill.
</details>

<details><summary><b>Q9.</b> `catchup=True` or `False`?</summary>

**A.** Use `True` when each run processes its own window and you really want history filled, as in an incremental ingest. Use `False` when the DAG always processes "current state", as in a full-refresh transform, where running 200 historical copies is meaningless.

Airflow 3 changed the default to `False`, so an ingest DAG that relied on the old default now silently leaves gaps after a pause. Set it explicitly on every DAG.
</details>

<details><summary><b>Q10.</b> How do you handle secrets?</summary>

**A.** Keep Connections and Variables in a secrets backend such as AWS Secrets Manager or SSM Parameter Store. Never hardcode them, never commit them to the repo, and never store them as plain-text Variables.

Also avoid a top-level `Variable.get()` in a DAG file. It runs on **every parse loop** and hammers the backend. Fetch inside the task, or use Jinja templating so the value resolves at render time.
</details>

---

## Operations

<details><summary><b>Q11.</b> How do you know a DAG is healthy?</summary>

**A.** Alert on two separate questions: "did it run?" and "did it run on time?". Finance cares about both.

- **Did it run:** failure callbacks to Slack.
- **On time:** in Airflow 2 this was SLA-miss callbacks. Airflow 3.0 removed SLAs, and **Deadline Alerts** (3.1+) replace them. On 3.0 you'd add an explicit freshness check.

Beyond that, watch task-duration trends (a task creeping from 2 to 9 minutes is a warning), retry rates and scheduler lag.
</details>

<details><summary><b>Q12.</b> Your DAG has been failing intermittently for a week. How do you approach it?</summary>

**A.** Look for the pattern first: same task, same time of day, same input? Intermittent failures almost always mean a **resource or race** problem rather than a logic bug. Common causes are a source API rate-limiting, a warehouse queue, or a file that isn't fully written when the task starts.

Then make it deterministic: idempotent tasks, bounded retries with backoff, and an explicit completeness check (a `_SUCCESS` marker, or an expected size) instead of assuming the file is whole. If it's still flaky, add logging around the boundary and let it fail loudly with context rather than retry silently.
</details>

<details><summary><b>Q13.</b> The scheduler is slow. What do you check?</summary>

**A.** Check DAG parse time first. Top-level code runs on every parse loop, so an API call or a heavy import at module level slows the whole scheduler. Keep DAG files thin and put the work inside tasks.

Then check the number of DAGs and tasks, `min_file_process_interval`, metadata-database performance (a common bottleneck), and whether one DAG has thousands of mapped tasks.
</details>

<details><summary><b>Q14.</b> How do you refactor a 6-hour monolith DAG people depend on?</summary>

**A.** Use the strangler pattern, as with any production refactor:
1. Stand up the new decomposed DAGs beside the monolith, writing to a `_v2` schema.
2. Run both for two weeks and diff the outputs nightly.
3. Cut consumers over, then delete the monolith.

Rewriting it in place over a weekend is how you spend the following month firefighting.
</details>

<details><summary><b>Q15.</b> XComs: when are they fine and when are they a smell?</summary>

**A.** XComs are fine for small metadata: a file path, a row count, a watermark, a manifest of keys.

They're a smell when they carry data. By default XComs live in the metadata database, so pushing a dataframe through them bloats the DB and couples tasks. Pass a **pointer**, such as an S3 key, and let the next task read it.
</details>

<details><summary><b>Q16.</b> How do you test Airflow code?</summary>

**A.** Keep the logic out of the operators so you can test it without Airflow at all. Then test at three levels:
- **DAG integrity tests:** import every DAG and assert no import errors or cycles. This catches most breakage in CI.
- **Unit tests** on plain Python functions that hold the business logic.
- **Integration tests** running a full DAG against a test target.
</details>

<details><summary><b>Q17.</b> What changed in Airflow 3 that you should know before an interview?</summary>

**A.** The five changes that bite are Assets replacing Datasets, removed SLAs, catchup defaulting to False, cron schedules with no data interval, and tasks that can no longer touch the metadata DB directly. Knowing them signals you've kept current.

- **Assets** replace Datasets (`from airflow.sdk import Asset`), with an `@asset` decorator.
- **SLAs are removed**; Deadline Alerts arrive in 3.1.
- **`catchup` defaults to `False`**.
- **Cron strings no longer create data intervals** by default (see Q2).
- **Task SDK / API server:** tasks talk to an API server instead of the metadata DB directly, so code doing raw ORM queries against Airflow's DB breaks. It also allows remote/edge workers.

Also removed: SubDAGs (use TaskGroups) and `execution_date` (use `logical_date`). On a migration, run `ruff` with the AIR rules to flag deprecated imports.
</details>
