# Snowflake — Questions

From [../data-engineering/snowflake-performance.md](../data-engineering/snowflake-performance.md). The JD bullets are query profiling, performance tuning, clustering, warehouse sizing and cost optimisation, and these questions cover those five plus ingestion.

If anything here doesn't click, the outside reading that explains it best is [SELECT — Snowflake query optimization](https://select.dev/posts/snowflake-query-optimization).

---

## Architecture & pruning

<details><summary><b>Q1.</b> Explain Snowflake's architecture in 30 seconds.</summary>

**A.** Storage and compute are separate, with a services layer on top.

- **Storage:** data as immutable, compressed columnar micro-partitions in cloud object storage.
- **Compute:** virtual warehouses, stateless clusters pointed at that storage.
- **Cloud services:** metadata, optimiser, security.

Because the two are separate, you can resize a warehouse in seconds, run ten warehouses against one table without contention, and clone a database without copying data. Tables can also be **Iceberg tables** in your own bucket, so "your data is locked in a proprietary format" is no longer a given.
</details>

<details><summary><b>Q2.</b> What is a micro-partition and why does it matter?</summary>

**A.** A micro-partition is the unit Snowflake stores and skips. Each one holds 50–500 MB of **uncompressed** data (much less on disk once compressed) and is columnar and immutable. For each one Snowflake keeps metadata: **min/max per column**, distinct counts, null counts.

It matters because that metadata drives **pruning**, the single biggest lever on query performance. Bridge: it's a Parquet row-group skip, done automatically on every table.
</details>

<details><summary><b>Q3.</b> What is pruning, and how do you tell whether it worked?</summary>

**A.** Pruning means skipping micro-partitions whose min/max can't match the filter. Skipped partitions cost nothing.

Check `partitions scanned / partitions total` in the Query Profile. Scanning 2% is healthy. Scanning 95% to return 100 rows means pruning failed, and *that's* the bug, not the warehouse size.
</details>

<details><summary><b>Q4.</b> Name three ways to accidentally kill pruning.</summary>

**A.** The most common real tuning win is rewriting a `WHERE` clause so it can prune, not resizing anything. Three ways to break it:

1. **A function on the filtered column.** `where to_date(created_at) = '2025-03-01'` can stop the optimiser from using min/max. Use a range: `>= '2025-03-01' and < '2025-03-02'`.
2. **Casting.** `where cast(id as varchar) = '123'`. Compare in the native type.
3. **Random insert order.** Every partition ends up holding the full value range, so min/max prunes nothing. Load in date order, or cluster.
</details>

---

## Query profiling

<details><summary><b>Q5.</b> A query that ran in 30 seconds now takes 8 minutes. How do you debug it?</summary>

**A.** Open the Query Profile and check pruning, spilling and join explosion, in that order. Only spilling is fixed by a bigger warehouse.

1. **Partition pruning ratio:** a high scan ratio with a small result means the predicate stopped pruning.
2. **Spilling:** `Bytes spilled to remote storage` is the bad sign, often many times slower.
3. **Join explosion:** compare a join node's output rows to its inputs. 1M ⋈ 1M producing 40M means the key isn't unique.

Also check whether data volume or the upstream grain changed, and whether the time was actually queueing (Q7).
</details>

<details><summary><b>Q6.</b> What's the difference between local and remote spilling?</summary>

**A.** **Local** spilling means the query exceeded warehouse memory and used the node's local disk. That's tolerable. **Remote** spilling means it exceeded local disk too and is writing to object storage, which is the bad one and often the single largest cause of a slow query.

Fix remote spilling by sizing up, or by filtering and aggregating earlier so less data flows through the join or sort.
</details>

<details><summary><b>Q7.</b> The profile shows high "queued (overload) time". What does that tell you?</summary>

**A.** The warehouse was saturated. That's a **concurrency** problem, not a query problem, so scale **out** with a multi-cluster warehouse instead of scaling up.

A bigger warehouse makes each query faster, but they still queue behind each other. Rule: queued time → scale out; one slow query → scale up.
</details>

<details><summary><b>Q8.</b> A join node emits far more rows than it takes in. What's happening?</summary>

**A.** The join key isn't unique on one side, so each row fans out into several. That's a performance bug and a **correctness** bug at once, because the extra rows inflate every downstream sum.

Fix the grain: dedup the right-hand side, or correct the join condition. Adding `distinct` hides the bug and makes it permanent.
</details>

---

## Clustering

<details><summary><b>Q9.</b> When should you add a clustering key, and when shouldn't you?</summary>

**A.** Add one only on a multi-terabyte table where you've measured bad pruning on a predicate queries use consistently.

**Should:** the table is large (Snowflake's guidance is typically multiple TB), queries consistently filter or join on the same columns, and you've *measured* poor pruning on that predicate.

**Shouldn't:**
- Small or medium tables, where natural pruning is already fine.
- Tables fully rewritten each run, since clustering starts over every time.
- High-churn tables, where reclustering costs more than the queries save.

Automatic Clustering bills credits in the background. On a table that isn't filtered by the key, it's pure waste.
</details>

<details><summary><b>Q10.</b> How do you order columns in a clustering key?</summary>

**A.** **Lowest cardinality first**: `cluster by (delivered_date, customer_id)`, not the reverse. That's Snowflake's own recommendation, with a maximum of about 3–4 columns.

A high-cardinality column first defeats the purpose, because nearly every partition ends up with a distinct value range. For a timestamp, cluster on an expression like `to_date(created_at)` rather than the raw value.
</details>

<details><summary><b>Q11.</b> How do you prove clustering was worth it?</summary>

**A.** Show that pruning improved **and** that the saved query credits exceed the reclustering credits.

`select system$clustering_information('fct_shipments', '(delivered_date)')` returns `average_depth`: how many partitions overlap for a typical value. Lower is better; close to 1 is well clustered.

Then compare reclustering credits in `AUTOMATIC_CLUSTERING_HISTORY` with the query credits saved. If clustering doesn't pay for itself, `alter table t drop clustering key`.
</details>

<details><summary><b>Q12.</b> What would you try before clustering?</summary>

**A.** Load in sorted order. That gives most of the benefit at zero ongoing cost, and it's often just an `ORDER BY` in the model that builds the table.

- For incremental models, an append in date order stays naturally clustered.
- For point lookups on a high-cardinality column (`where email = ...`), **Search Optimization** beats clustering.
- For occasional scan-heavy outliers, **Query Acceleration** avoids sizing the whole warehouse for one query.
</details>

---

## Warehouse sizing

<details><summary><b>Q13.</b> How do you decide what size a warehouse should be?</summary>

**A.** Test it, because **cost = size × time**. Each size up doubles credits per hour (on standard warehouses), so if doubling halves the runtime, the cost is identical and you finished sooner.

- Near-linear speedup → free speed, take it.
- Small improvement → you're paying more for little, stay small.
- Query spills to remote storage → sizing up is usually a straight win, because removing the spill can give more than a 2× speedup.

Run the same workload on two sizes and compare **credits consumed**, not runtime.
</details>

<details><summary><b>Q14.</b> Counterintuitively, when is a bigger warehouse cheaper?</summary>

**A.** When it removes spilling. A query spilling to remote storage on a Medium might run more than 4× faster on a Large with no spill. The Large burns 2× the credits per hour for less than a quarter of the time, so you pay less and finish sooner.

People forget that cost has a time term. "Bigger is more expensive" is only true when runtime doesn't fall at least in proportion.
</details>

<details><summary><b>Q15.</b> Why separate warehouses per workload?</summary>

**A.** Two reasons: workloads stop competing for the same compute, and **spend becomes attributable**. You can't optimise what you can't attribute.

- `LOADING_WH` XS: COPY is I/O-bound, so size buys little.
- `TRANSFORM_WH` M–L: dbt, the one place size helps.
- `BI_WH` S multi-cluster: dashboards need concurrency, not power.
- `ADHOC_WH` XS with a hard resource monitor: contains the accidental cross join.
</details>

<details><summary><b>Q16.</b> Why not set AUTO_SUSPEND to 5 seconds?</summary>

**A.** Because every suspend throws away the warehouse's local disk cache, and every resume bills a minimum of 60 seconds. Very short suspends cost more than the idle time they save. 60 seconds is the usual sweet spot; BI warehouses with bursty traffic sometimes justify a few minutes.
</details>

---

## Cost

<details><summary><b>Q17.</b> Our Snowflake bill is $85k/month and growing. Where do you start?</summary>

**A.** Measure first, then make the reversible config changes before tuning queries.

**Measure:**
- `WAREHOUSE_METERING_HISTORY` for spend by warehouse.
- `QUERY_ATTRIBUTION_HISTORY` for credits per query.
- `ACCESS_HISTORY` for tables nobody reads.

**Then, in order of effort:**
1. `AUTO_SUSPEND = 60` everywhere.
2. Split warehouses by workload.
3. Right-size down and measure.
4. Query tags for attribution.
5. Delete unused models and tables.
6. Fix the top 10 queries.
7. Resource monitors on ad-hoc.

Config changes go first because they're reversible and visible within a week. Query tuning is higher value but slower.
</details>

<details><summary><b>Q18.</b> How do you attribute credits to a specific dbt model?</summary>

**A.** Tag every query with the model that issued it, then group credits by tag.

Set `query_tag` in the model config (or `dbt_project.yml`), or use `query-comment` for richer metadata. Then group `QUERY_ATTRIBUTION_HISTORY` joined to `QUERY_HISTORY` by tag, and every credit traces back to a model.

Without this, "the warehouse costs $12k" can't be acted on.
</details>

<details><summary><b>Q19.</b> ACCOUNT_USAGE or INFORMATION_SCHEMA?</summary>

**A.** Use `ACCOUNT_USAGE` for analysis and `INFORMATION_SCHEMA` for "what is happening right now".

- **ACCOUNT_USAGE:** 365 days of retention, account-wide, but latency of about 45 minutes to a few hours depending on the view.
- **INFORMATION_SCHEMA:** near real-time, but scoped per database, with retention that varies by table function (7 days for `QUERY_HISTORY`, 14 for `COPY_HISTORY`, 6 months for `WAREHOUSE_METERING_HISTORY`).

Using ACCOUNT_USAGE to debug a query running this minute is a classic mistake: the data isn't there yet.
</details>

<details><summary><b>Q20.</b> How do you reduce storage cost?</summary>

**A.** Storage is rarely the problem next to compute (approx. $23/TB/month on capacity pricing in US regions; on-demand costs more). Three moves still help:
- Make staging tables **transient**, which removes Fail-safe.
- Keep Time Travel at 1 day, except on tables where you need more.
- Check `TABLE_STORAGE_METRICS` for Time Travel and Fail-safe bytes on large, high-churn tables. That overhead can exceed the table itself.
</details>

---

## Features

<details><summary><b>Q21.</b> What's a zero-copy clone and why does it matter for refactoring?</summary>

**A.** A clone is a production-shaped copy created in seconds, billed only for the data that later diverges. `create database analytics_ci clone analytics_prod` is the whole command.

It's the backbone of safe production work. CI runs against real volume, real skew and real edge cases instead of a stale sample, and a clone is a free rollback point before any risky migration.
</details>

<details><summary><b>Q22.</b> What does SWAP WITH do?</summary>

**A.** It atomically exchanges two tables. It's a metadata operation, so it's effectively instant and readers never see a half-migrated state. Rollback is simply a second swap, which makes it the standard way to cut over a rebuilt table without downtime.
</details>

<details><summary><b>Q23.</b> Someone dropped a production table an hour ago. Options?</summary>

**A.** Within the Time Travel window, `UNDROP TABLE t` restores it. For bad data rather than a drop, `select * from t at (offset => -3600)` reads the earlier state so you can rebuild.

Default retention is 1 day. You can raise `DATA_RETENTION_TIME_IN_DAYS` up to 90 on Enterprise edition. Raising it deliberately before a risky migration and lowering it afterwards is good practice. After Time Travel comes 7 days of Fail-safe, which only Snowflake support can recover from.
</details>

<details><summary><b>Q24.</b> Why is QUALIFY worth knowing?</summary>

**A.** `QUALIFY` filters on a window function without a subquery, which makes it the idiomatic dedup:
```sql
select * from raw.shipments
qualify row_number() over (partition by shipment_id
                           order by updated_at desc, _loaded_at desc) = 1
```
The catch: the ordering must be **total**. Over a non-unique ordering, `ROW_NUMBER` can return different rows on different runs, and you get a "flaky" model nobody can reproduce.
</details>

<details><summary><b>Q25.</b> What are the three caching layers?</summary>

**A.** Result cache, local disk cache and metadata cache.

- **Result cache:** 24h, free, but it needs the same query text and unchanged data. `current_timestamp()` in a dashboard query defeats it entirely, a real and commonly missed cost bug.
- **Local disk cache:** the warehouse's disk; lost on suspend.
- **Metadata cache:** `count(*)`, `min` and `max` often return with no warehouse running at all.
</details>

---

## Ingestion & pipelines

<details><summary><b>Q26.</b> COPY INTO, Snowpipe, or Snowpipe Streaming?</summary>

**A.** Pick by how the data arrives: files on a schedule, files continuously, or rows as a stream.

- **`COPY INTO`** from a stage: batch files on a schedule, orchestrated by Airflow. Cheapest and easiest to reason about.
- **Snowpipe:** files landing continuously in S3, loaded via event notifications within about a minute. Serverless and billed per use; no warehouse to manage.
- **Snowpipe Streaming:** rows, not files. Kafka (via the connector) or an SDK writes directly, data is queryable in seconds, and there are no small files to manage. The high-performance architecture is GA (approx. <10 s ingest-to-query, checked 2026-09).

For the trucks: at 10k trucks, Firehose → S3 → Snowpipe is plenty for analytics. Pick Streaming when the warehouse itself needs data in seconds, or when you already have Kafka. "Snowflake can't do streaming" is an outdated answer.
</details>

<details><summary><b>Q27.</b> Dynamic Tables, Streams + Tasks, or dbt?</summary>

**A.** Use **dbt** for the modelled batch layer. Use **Dynamic Tables** for a declarative, near-real-time layer, and **Streams + Tasks** when you need imperative control.

- **Dynamic Tables:** you write a `SELECT` and a `TARGET_LAG` ("1 minute"), and Snowflake refreshes it incrementally when it can. Minimal code, no scheduler.
- **Streams + Tasks:** a stream records changes on a table and a task runs your `MERGE` on a schedule. Pick them for custom logic like deletes, SCD handling or calling procedures.
- **dbt:** tests, lineage, CI and review. It can also materialise `dynamic_table`, so the choice isn't either/or.

Trade-off: warehouse-native options remove an orchestrator but can't coordinate work outside Snowflake. They also refresh continuously, and continuous refresh bills continuously.
</details>

<details><summary><b>Q28.</b> "Isn't Snowflake a lock-in, with data in a proprietary format?"</summary>

**A.** Less than it used to be. **Iceberg tables** store data as Parquet plus Iceberg metadata in your own cloud storage, readable by Spark, Trino or Databricks, while Snowflake keeps doing the compute.

- **Pick native tables** when Snowflake is the only engine. You get the full feature set and the least to operate.
- **Pick Iceberg** when several engines must read the same data, or when an exit path is a hard requirement.

Trade-off: Iceberg means you own the storage and more of the lifecycle: file layout, catalog choice, cross-region costs. Some features behave differently from native tables. The honest answer names both.
</details>
