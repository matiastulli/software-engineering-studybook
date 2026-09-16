# dbt — Questions

---

## Fundamentals

<details><summary><b>Q1.</b> What is dbt, precisely? Does it process data?</summary>

**A.** No. dbt has no compute of its own: it compiles Jinja + SQL into plain SQL and runs it against the warehouse, which does all the work. `dbt run` issues `CREATE TABLE AS SELECT` / `MERGE` statements, and your data never passes through dbt.

It's the **T** in ELT, so data must already be loaded. It can't do the E or the L: no SFTP, no API calls, no moving bytes. Think "a SQL generator plus a dependency graph".
</details>

<details><summary><b>Q2.</b> Walk me through your project structure.</summary>

**A.** Four layers, each with a strict contract, so a wrong number becomes a four-step bisect instead of a search through 400 models.

- **staging:** views, one per source table. Rename to convention, cast types and timezones, dedupe. **No joins, no business logic.**
- **intermediate:** ephemeral models or tables holding joins and the complex logic. Not exposed outside the project.
- **marts:** tables or incremental models that are business-grade, tested, documented and contracted. The only layer BI touches.
- **snapshots:** SCD2 history.
</details>

<details><summary><b>Q3.</b> What are the materializations and when do you use each?</summary>

**A.** Start with `table` and move to `incremental` only when the rebuild time or cost actually hurts, because incremental adds real complexity.

| Materialization | Use |
| --- | --- |
| **view** | Staging. No storage, always fresh, computed on every read |
| **table** | Rebuilt each run. Simple and correct: the default until it's too slow |
| **incremental** | Large facts you can't afford to rebuild |
| **ephemeral** | Inlined as a CTE. Intermediate logic you don't want materialised |
| **materialized_view** / **dynamic_table** | Warehouse-maintained refresh. On Snowflake use `dynamic_table` |
| **snapshot** | SCD2 history of a mutating source |
</details>

---

## Incremental models

<details><summary><b>Q4.</b> Write an incremental model and explain each part.</summary>

**A.** One file handles both the first build and the updates: `is_incremental()` switches on the filter, `merge` on a unique key makes re-runs safe, and a lookback catches late data.

```sql
{{ config(materialized='incremental', unique_key='shipment_id',
          incremental_strategy='merge', on_schema_change='append_new_columns') }}

select * from {{ ref('stg_shipments') }}
{% if is_incremental() %}
  where _loaded_at >= (select dateadd(day, -3, max(_loaded_at)) from {{ this }})
{% endif %}
```

- `is_incremental()` is false on the first build and on `--full-refresh`, so the same file builds from scratch or updates.
- `unique_key` + `merge` makes reprocessing idempotent.
- The **3-day lookback** re-reads recent rows so late arrivals aren't skipped.
- Filter on the **load timestamp** (`_loaded_at`) when you can. A business timestamp like `delivered_at` can be days old when the row lands, so it slips behind the watermark.
</details>

<details><summary><b>Q5.</b> Which incremental strategy on Snowflake, and why?</summary>

**A.** Use `merge` by default. Snowflake has a real `MERGE`, so dbt matches on `unique_key` and updates in place.

- **`delete+insert`:** when you want to replace whole slices, like the last 3 days, without row-level matching. It's often cheaper than `merge` on very large tables.
- **`microbatch`** (dbt 1.9+): when the fact is time-series and you want dbt to process one day per query, with per-batch retries and easy backfills.
- **`append`:** only for immutable event logs where duplicates are impossible.

**Trap:** on Snowflake, `insert_overwrite` replaces the **entire table**, not a partition. Unlike BigQuery or Spark, it does no partition overwrite.
</details>

<details><summary><b>Q6.</b> What's the danger with incremental models nobody mentions?</summary>

**A.** Over time the incremental path and the full-refresh path **drift apart**. Someone edits the `is_incremental()` branch, the two stop producing the same result, and you don't find out until an auditor does.

Mitigation: run a full refresh on a schedule (monthly, on a clone) and diff row counts and measure sums against the incrementally built table. Never let a model become buildable *only* incrementally.
</details>

<details><summary><b>Q7.</b> What does `on_schema_change` do?</summary>

**A.** It controls what an incremental model does when its columns change. The default is a trap.

- `ignore` (default): new columns silently don't appear in the target.
- `append_new_columns`: usually what you want.
- `sync_all_columns`: adds and removes columns.
- `fail`: loudest, good for regulated marts.

With `ignore`, you add a column, the build succeeds, and the column silently isn't there. None of these options backfill history for the new column; that needs a full refresh.
</details>

---

## Snapshots & history

<details><summary><b>Q8.</b> What problem do snapshots solve?</summary>

**A.** Snapshots keep history the source overwrites in place. A rate card gets updated and March's price is otherwise gone forever. dbt records every version with `dbt_valid_from` / `dbt_valid_to`, which is a Type-2 SCD.

```sql
{% snapshot rate_cards_snapshot %}
{{ config(target_schema='snapshots', unique_key='rate_card_id',
          strategy='timestamp', updated_at='updated_at',
          hard_deletes='invalidate') }}
select * from {{ source('postgres', 'rate_cards') }}
{% endsnapshot %}
```

`hard_deletes` (dbt 1.9+) replaces the older `invalidate_hard_deletes=True`. Since 1.9 you can also define snapshots in YAML.

**A snapshot cannot be backfilled after the fact:** history you didn't capture is gone. So it's the first thing to build and the thing never to break.
</details>

<details><summary><b>Q9.</b> How do you join to a snapshot correctly?</summary>

**A.** Join point-in-time, to the version valid on the event date, not to the current row:
```sql
left join rates r
       on r.lane_id = s.lane_id
      and s.delivered_date >= r.dbt_valid_from
      and s.delivered_date <  coalesce(r.dbt_valid_to, '9999-12-31')
```
Joining to the *current* rate card silently restates history every time pricing changes. March's number moves, and finance stops trusting you.
</details>

<details><summary><b>Q10.</b> `timestamp` or `check` snapshot strategy?</summary>

**A.** Use `timestamp` when the source has a reliable `updated_at`; it's cheaper because it compares one column. Use `check` when there's no reliable `updated_at`: dbt compares a list of columns (or all of them) to detect change, which is slower on wide tables.

With either strategy you only see the state **at snapshot time**. Two updates between runs collapse into one, and a change that reverts before the next run is invisible. If you need every intermediate version, you need CDC, not snapshots.
</details>

---

## Testing & contracts

<details><summary><b>Q11.</b> How do you structure tests?</summary>

**A.** Two tiers with different severities, plus source freshness.

- **Structural** (`unique`, `not_null`, `relationships`, `accepted_values`): severity **error**. A duplicated `shipment_id` double-counts revenue, so stop the pipeline.
- **Business** (reconciliation to the GL, row counts vs a 7-day average, plausible ranges): usually **warn**. Investigate, but don't halt month-end close.

**Source freshness** is the only one that catches *absent* data.
</details>

<details><summary><b>Q12.</b> Why is source freshness the most important test?</summary>

**A.** Because every other test passes happily on an empty increment. A carrier that quietly stops sending files produces no nulls, no duplicates and no failures, just a number that's slowly wrong.

`dbt source freshness` with `warn_after` / `error_after` thresholds is the only built-in check that finds missing-data bugs.
</details>

<details><summary><b>Q13.</b> Write a test finance would actually care about.</summary>

**A.** A singular test that reconciles warehouse revenue to the general ledger. It passes when it returns zero rows:
```sql
-- tests/assert_revenue_reconciles_to_gl.sql
select d.month, d.warehouse_revenue, g.gl_revenue
from {{ ref('fct_revenue_monthly') }} d
join {{ ref('stg_quickbooks__gl') }} g using (month)
where abs(d.warehouse_revenue - g.gl_revenue) > 0.01 * g.gl_revenue
```
Structural tests prove the data is well-formed; this one proves it's *right*. Note that the inner join ignores months missing from either side, so pair it with a count-of-months check.
</details>

<details><summary><b>Q14.</b> What are contracts and when do you enforce them?</summary>

**A.** A contract is a declared schema the build must match. `contract: {enforced: true}` declares column names and types, and the build fails if the model's output doesn't match.

Enforce contracts on **marts**, meaning anything BI, reverse ETL or another team consumes. They turn "a dashboard broke mysteriously last Tuesday" into "the build failed in CI with a clear message". Skip them on staging, where churn is expected.
</details>

---

## Workflow

<details><summary><b>Q15.</b> How do you make CI fast enough that people don't skip it?</summary>

**A.** Slim CI: build only what changed and defer everything else to prod.

`dbt build --select state:modified+ --defer --state ./prod-manifest` builds the changed models plus their children and reads unchanged parents from prod. On a 200-model project that can cut CI from tens of minutes to a few.

Run it against a **zero-copy clone of prod**, so it sees real volume and real edge cases rather than a stale sample.
</details>

<details><summary><b>Q16.</b> `dbt run` vs `dbt build`?</summary>

**A.** Use `build` in CI and production, almost always. `run` only executes models. `build` runs models, tests, snapshots and seeds **in dependency order**, so a model's tests run right after it and a failure stops its children from building on bad data.
</details>

<details><summary><b>Q17.</b> Explain `ref()` and why it matters.</summary>

**A.** `ref()` resolves the right table for each environment and builds the DAG. `{{ ref('stg_shipments') }}` compiles to the actual relation for the current target, so the same code points at dev, CI or prod without edits.

More importantly, dbt derives execution order and lineage from `ref()` calls. A hardcoded table name doesn't just skip environment handling: it removes that dependency from the graph, so the model may build before its parent.
</details>

<details><summary><b>Q18.</b> When would you use a macro, and when is it a mistake?</summary>

**A.** Use a macro when the same logic repeats across many models; stop when readers can no longer see what the SQL does.

- **Good:** a currency conversion or date spine used in fifteen models, or `dbt_utils` helpers.
- **Bad:** wrapping every model in layers of Jinja until nobody can read the compiled SQL.

The test: if a new engineer can't tell what a model does without running `dbt compile`, the abstraction cost more than it saved.
</details>

<details><summary><b>Q19.</b> What does audit_helper do?</summary>

**A.** It compares two relations and reports the differences, which is how you prove a refactored model matches the old one before cutting over.

- `compare_relations` gives row-level diffs.
- `compare_column_values` finds which column drifts.
- `compare_queries` compares arbitrary logic.
</details>

<details><summary><b>Q20.</b> How do you document a project so it's actually used?</summary>

**A.** Make documentation part of every PR rather than a separate project nobody finishes.

- Descriptions in `.yml` next to the tests.
- `dbt docs generate` for the lineage catalogue.
- **Exposures** declaring which dashboards depend on which models, so a PR shows what would break.
</details>

<details><summary><b>Q21.</b> `merge` with a lookback, or `microbatch`?</summary>

**A.** Use `merge` with a lookback for most models. Use `microbatch` when a large time-series fact needs cheap backfills and per-day retries.

- **Merge + lookback:** one query per run over the trailing N days. Simple, but a 6-month backfill is one enormous query that fails all-or-nothing.
- **Microbatch** (dbt 1.9+): you declare `event_time`, `batch_size='day'`, `begin` and `lookback`. dbt runs one query per day, retries failed batches individually, and backfills with `--event-time-start/--event-time-end`.

Trade-off: microbatch assumes each row belongs to exactly one time batch. If late updates change a row's `event_time`, or the grain isn't time-based, stay on `merge`.
</details>

<details><summary><b>Q22.</b> Data tests vs unit tests in dbt: what's the difference?</summary>

**A.** Data tests check the **data** after a build; unit tests (dbt 1.8+) check the **logic** before it touches real data.

- **Data tests** (`unique`, `not_null`, singular tests) run on the actual output.
- **Unit tests:** you give a model fixed input rows (`given`) and assert the output rows (`expect`), without depending on production data.

Use unit tests for tricky SQL: a point-in-time join, a timezone bucket, a `case` that encodes a pricing rule. They catch "the logic is wrong" in CI, which data tests only catch after bad data lands. Don't unit-test simple renames in staging; that's padding.
</details>
