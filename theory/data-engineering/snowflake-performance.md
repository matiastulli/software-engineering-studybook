# Snowflake — Profiling, Tuning, Clustering, Sizing & Cost

## TL;DR

- **Storage and compute are separate.** Tables are immutable micro-partitions in object storage, and warehouses are stateless compute pointed at them. That is why resizing is instant and clones are free.
- **The first performance question is how many partitions the query read.** Pruning uses per-partition min/max. A function on the filter column, or random load order, kills it.
- **For a slow query, check three things in the Query Profile:** pruning ratio, remote spilling, join explosion. Only spilling is fixed by a bigger warehouse.
- **Queued means scale out (multi-cluster). One slow heavy query means scale up.** Doubling size doubles the rate and often halves the runtime, for the same cost.
- **Clustering and Search Optimization bill continuously.** Try loading in sorted order first, and prove the saving exceeds the cost.

---

## 1. The problem

`fct_pings` holds 2 TB of truck GPS data. A dispatch dashboard runs `where date(event_ts) = current_date - 1` every 5 minutes on a Medium warehouse with `AUTO_SUSPEND = 600`. Each run takes 90 s and scans 97% of partitions. With a run every 5 min and a 10-min suspend timer, the warehouse never sleeps: **4 credits/hour × 24 h ≈ 96 credits/day** for a query that should read one day out of ~2 years (~1/700 of the table). Someone proposes an XL warehouse.

Resizing would make the same waste faster at 4× the rate. The fix is a `WHERE` clause.

---

## 2. Micro-partitions and pruning — the foundation

Snowflake stores every table as **micro-partitions**:
- 50–500 MB of *uncompressed* data each, stored compressed and columnar.
- Immutable: DML writes new partitions.
- Per-partition metadata includes each column's **value range (min/max)** and distinct count.

**Pruning:** for `where event_ts >= '2026-09-01' and event_ts < '2026-09-02'`, Snowflake skips every partition whose `event_ts` range can't match. Skipped partitions cost nothing.

**Bridge:** micro-partition pruning ≈ Delta file skipping ≈ Parquet row-group skipping. Unlike Hive folder partitioning it is **range-based**, so it only works if each partition holds a narrow range of the filter column. Data loaded in time order gets that for free.

```sql
select query_id, partitions_scanned, partitions_total,
       partitions_scanned / nullif(partitions_total, 0) as scan_ratio
from snowflake.account_usage.query_history
where query_id = '<id>';
```
A 2% scan ratio is healthy. 95% to return 100 rows means pruning failed, and *that* is the bug, not the warehouse size.

### What kills pruning

| Anti-pattern | Why | Fix |
| --- | --- | --- |
| `where date(event_ts) = '2026-09-01'` | A function on the column hides it from min/max | `where event_ts >= '2026-09-01' and event_ts < '2026-09-02'` |
| `where cast(truck_id as varchar) = '123'` | Same | Compare in the native type |
| Filter on a column uncorrelated with load order (`speed_kmh > 80`) | Every partition spans the full range | Cluster on it if it's a hot filter, or accept the scan |
| Random insert order, e.g. a full rebuild without `order by` | Every partition holds every date | Load in date order, or cluster |

**Decision rule:** before touching warehouse size, make the predicate prunable. It is the most common real-world tuning win.

---

## 3. Reading a Query Profile

Open Snowsight → Query History → the query → **Query Profile**. Read in this order:

1. **The most expensive node** (% of execution time). Start there.
2. **Pruning.** On `TableScan`, compare partitions scanned vs total.
3. **Spilling** (statistics panel):
   - `Bytes spilled to local storage`: exceeded memory, used the warehouse's local disk. Tolerable.
   - `Bytes spilled to remote storage`: exceeded local disk too, writing to object storage. **Severe**, often many times slower.
4. **Join explosion.** Output rows ≫ input rows means a non-unique join key. That is a correctness bug (duplicates) *and* a performance bug.
5. **Queueing.** `Queued overload time` means the warehouse is saturated. It's a concurrency problem, not a query problem.

| Symptom in profile | Cause | Fix |
| --- | --- | --- |
| High scan ratio, small result | Pruning failure | Rewrite the predicate, then consider clustering or Search Optimization |
| Remote spilling | Working set too big for the warehouse | Filter or aggregate earlier, or size up |
| Join output ≫ inputs | Non-unique join key | Fix the grain by deduping the right side (see [sql-advanced.md §3](sql-advanced.md)). Don't paper over it with `distinct` |
| Most time in one `Sort` | `order by` on a huge intermediate | Sort after aggregating, or drop it |
| High queued time | Concurrency | Multi-cluster warehouse |
| High `Bytes sent over network` | Big data redistribution for a join or aggregate | Pre-aggregate or filter before joining |

**Bridge:** this is Spark's diagnosis with other names. Pruning ↔ `PartitionFilters`, spilling ↔ executor spill and GC, join explosion ↔ a join node's row counts, network bytes ↔ `Exchange` ([pyspark.md](pyspark.md)).

> *"I'd open the Query Profile and check three things in order: partition pruning ratio, remote spilling, and whether a join explodes row counts. Those cover most regressions, and only spilling is solved by a bigger warehouse."*

---

## 4. Clustering

Tables are naturally clustered by insert order. **A clustering key is for large tables whose natural order doesn't match how they're filtered.**

```sql
alter table fct_pings cluster by (to_date(event_ts), truck_id);
```
Automatic Clustering then reclusters in the background, **and bills credits for it continuously.** A clustering key can contain an expression. The key itself is what Snowflake maintains, which is different from a function in a `WHERE`.

**Cluster when all of these hold:**
- The table is large (rule of thumb: ≥1 TB, approx.).
- Queries consistently filter or join on the same columns.
- You've *measured* poor pruning on them.

**Don't cluster:**
- Small or medium tables.
- Tables fully rebuilt each run. Load them sorted instead.
- High-churn tables where reclustering costs more than it saves.
- Keys with more than 3–4 columns.

**Order key columns from lower to higher cardinality**, and reduce very high-cardinality columns first, e.g. a timestamp → `to_date(event_ts)`.

```sql
select system$clustering_information('fct_pings', '(to_date(event_ts), truck_id)');
```
Watch `average_depth`, the number of overlapping partitions for a value (lower is better). Compare reclustering credits (`AUTOMATIC_CLUSTERING_HISTORY`) against query credits saved. If clustering doesn't pay, `alter table … drop clustering key`.

**Cheaper alternatives, in order:**
1. **Load in sorted order**: an `order by` in the dbt model, or an incremental `delete+insert` / `microbatch` model loaded by date (on Snowflake, dbt's `insert_overwrite` replaces the whole table, not a partition). Most of the benefit, zero ongoing cost.
2. **Search Optimization Service** for **point lookups** on high-cardinality columns (`where load_id = …`). Billed continuously.
3. **Query Acceleration Service** for occasional scan-heavy outlier queries, so the whole warehouse isn't sized for them.

**Bridge:** automatic clustering ≈ Databricks liquid clustering ([databricks.md §3](databricks.md)).

**Decision rule:** sorted load first, a clustering key only on large, measured, stable-filter tables, and Search Optimization for needle-in-haystack lookups.

---

## 5. Warehouse sizing: scale up vs scale out

| Size | XS | S | M | L | XL | … up to 6XL |
| --- | --- | --- | --- | --- | --- | --- |
| Credits/hour (standard warehouse) | 1 | 2 | 4 | 8 | 16 | doubles each step |

Billing is **per second with a 60-second minimum** each time a warehouse starts or resumes (checked 2026-09, Snowflake docs).

**Cost = rate × time.** Doubling the size doubles the rate. If the runtime halves, the cost is identical and you get the result sooner.
- Near-linear speedup → free speed, so take it.
- Less than ~30% speedup → you pay more for little, so stay small.
- Remote spilling → sizing up usually wins outright, because removing the spill gives a superlinear speedup.

Test with the real workload on two sizes and compare **credits**, not seconds.

**Scale up vs scale out:**
- **Scale up** (bigger size) for one slow, heavy query: more memory and threads per query.
- **Scale out** (multi-cluster, `MIN_CLUSTER_COUNT` / `MAX_CLUSTER_COUNT`, Enterprise edition and above) for many concurrent queries queueing, the BI-dashboard case. `SCALING_POLICY = STANDARD` favours latency and `ECONOMY` favours cost.

**One warehouse per workload**, so they don't contend and spend is attributable:

| Warehouse | Size | Why |
| --- | --- | --- |
| `LOADING_WH` | XS | `COPY INTO` is I/O-bound. Size buys little |
| `TRANSFORM_WH` | M–L | dbt. The place where size genuinely helps |
| `BI_WH` | S, multi-cluster | Concurrency, not raw power |
| `ADHOC_WH` | XS + resource monitor | Contains the accidental cross join |

Use `AUTO_RESUME = TRUE` and `AUTO_SUSPEND = 60` as a sane default. Suspending more aggressively than ~60 s rarely helps: each resume bills a minimum minute and can drop the local disk cache.

**Decision rule:** queued time → scale out. One slow query → fix pruning, then scale up if it spills. Fast but expensive → size down.

---

## 6. Caching — three layers

| Layer | Where | Invalidated / defeated by |
| --- | --- | --- |
| **Result cache** | Cloud services, no warehouse needed | Kept 24 h and reset on each reuse, up to 31 days. Requires the **exact same query text** (case and aliases matter), unchanged underlying data, and no non-deterministic functions such as `current_timestamp()` |
| **Local disk cache** | Warehouse nodes' SSD | Warehouse suspend or resize can drop it |
| **Metadata** | Cloud services | `count(*)`, and `min`/`max` on many column types, can answer without scanning |

**The classic cost bug:** a dashboard injects `current_timestamp()` or a changing literal into every query, so the result cache never hits and the warehouse never suspends. Parameterize to a stable date instead.

---

## 7. Cost model and attribution

**Compute dominates the bill.**
- **Storage:** approx. $23/TB/month compressed (AWS US East capacity rate, checked 2026-09; varies by region and contract). Time Travel and Fail-safe add to it.
- **Cloud services** (compilation, metadata) is billed only for the part above **10% of daily warehouse usage**. Worth checking if you fire huge numbers of tiny queries.

### Attribute spend with query tags

In dbt-snowflake, set `query_tag` as a config. It's applied with `alter session set query_tag` around each model:
```yaml
# dbt_project.yml
models:
  trucks:
    +query_tag: dbt_trucks        # or override the set_query_tag() macro to use model.name
```
```sql
select query_tag,
       count(*)                        as queries,
       sum(credits_attributed_compute) as credits
from snowflake.account_usage.query_attribution_history
where start_time >= dateadd(day, -7, current_date)
group by 1 order by credits desc limit 25;
```
`QUERY_ATTRIBUTION_HISTORY` excludes warehouse **idle time** and very short queries (≤ ~100 ms), and its latency can reach several hours. For runtimes, join to `QUERY_HISTORY` on `query_id`.

| `ACCOUNT_USAGE` view | Answers |
| --- | --- |
| `WAREHOUSE_METERING_HISTORY` | Credits per warehouse per hour, including idle |
| `QUERY_HISTORY` | Runtime, bytes scanned, spilling, pruning per query |
| `QUERY_ATTRIBUTION_HISTORY` | Credits per query (no idle) |
| `ACCESS_HISTORY` | Objects each query touched: "is this table still used?" |
| `TABLE_STORAGE_METRICS` | Active vs Time Travel vs Fail-safe bytes |
| `AUTOMATIC_CLUSTERING_HISTORY` | What reclustering costs |

`ACCOUNT_USAGE` is not real time: latency is **45 min to 3 h** depending on the view, with **1 year** of retention. `INFORMATION_SCHEMA` is near real time but retains **7 days to 6 months** depending on the view, and is scoped to one database. Use it for "what's running now" (checked 2026-09, Snowflake docs).

### Storage levers

- **Transient tables** have no Fail-safe. **dbt-snowflake creates tables as transient by default.** Set `transient: false` only for tables you can't rebuild.
- **Time Travel** defaults to 1 day. Raising it to 90 on a large, high-churn table multiplies storage. Raise it before a risky migration, then lower it.
- **Fail-safe** is 7 days, not configurable, and applies to permanent tables only.

**Decision rule:** find the top 25 query tags by credits, then fix pruning or sizing on the top 3. Check `WAREHOUSE_METERING_HISTORY` minus attributed credits to see idle waste.

---

## 8. Features worth naming

| Feature | Use |
| --- | --- |
| **Zero-copy clone** | Full-size test environment instantly. Storage billed only on divergence |
| **`SWAP WITH`** | Atomic table exchange for instant cutover and rollback |
| **Time Travel / `UNDROP`** | Recover a table someone broke an hour ago |
| **Streams + Tasks** | Table-level CDC plus scheduled SQL. Enough for warehouse-internal pipelines |
| **Dynamic Tables** | Declare a query and a target lag, and Snowflake refreshes it incrementally where it can |
| **Snowpipe / Snowpipe Streaming** | File micro-batch ingestion / row-level streaming ingestion |
| **Materialized Views** | Auto-maintained, but single table and no joins. Narrower than people expect |
| **`QUALIFY`** | Dedup without a subquery. Pattern and tie-breaker gotcha in [sql-advanced.md §3](sql-advanced.md) |

---

## 9. Tuning checklist

1. **Is it pruning?** `partitions_scanned / partitions_total`. Fix the predicate first.
2. **Is it spilling to remote?** Reduce the working set, or size up.
3. **Is a join exploding?** Compare rows in vs out. Usually a grain bug.
4. **Is it queueing?** Scale out, not up.
5. **Can it hit the result cache?** Remove non-deterministic functions from repeated queries.
6. **Is it doing unneeded work?** `select *` on wide tables, a pointless `order by`, a `distinct` hiding a bad join.
7. **Only now:** a clustering key or Search Optimization, with ongoing cost measured against the saving.

---

## Common wrong answers

- **"The query is slow, so use a bigger warehouse."** That only helps with spilling or a legitimately heavy scan. With a pruning failure you pay 2× the rate to scan the same useless partitions.
- **"Dashboards are slow at 9 am, so size up."** Queued time is concurrency. Use a multi-cluster warehouse, where the extra clusters exist only during the peak.
- **"Add a clustering key to every big table."** Reclustering bills forever. Fully rebuilt tables should simply load sorted, and point lookups want Search Optimization.
- **"Set `AUTO_SUSPEND = 1` second to save money."** Each resume bills a 60 s minimum and can lose the disk cache. About 60 s is the sane floor.
- **"`distinct` fixed the duplicate rows."** It hid a non-unique join key and added a big aggregation. Fix the grain.

---

## Self-check

<details><summary><b>Q1.</b> A query returning 200 rows scans 1,900 of 2,000 partitions. Name two likely causes and the fixes.</summary>

1. The predicate wraps the column in a function or cast (`date(event_ts) = …`), which hides it from min/max metadata. Rewrite it as a native-type range.
2. The table's load order doesn't correlate with the filter column, so every partition spans the full range. Load sorted, and if the table is large with a stable filter, add a clustering key and measure `average_depth`.

</details>

<details><summary><b>Q2.</b> Queued time is high on the BI warehouse at 9 am, but each query runs fast once it starts. Scale up or out, and why?</summary>

Scale out with a multi-cluster warehouse (Enterprise edition+). The bottleneck is concurrency, not per-query power. A bigger single warehouse doesn't add parallel slots as cheaply, and multi-cluster only runs the extra clusters during the peak.

</details>

<details><summary><b>Q3.</b> A dbt model got 3× slower after a join was added; the profile shows 5M rows in, 60M rows out of the join, plus remote spilling. What do you do first?</summary>

Fix the join grain first. The right side isn't unique on the key, so dedup it or join on the full key. The explosion is both a correctness bug (duplicate rows) and the reason the working set spills. Resizing would hide it while producing wrong numbers.

</details>

<details><summary><b>Q4.</b> The same dashboard query runs every 5 minutes and never hits the result cache. What's the likely cause?</summary>

The query text changes each run (an injected timestamp or literal), it uses a non-deterministic function like `current_timestamp()`, or the underlying table changes between runs. Parameterize to a stable value such as `current_date - 1` computed once, and schedule loads so data doesn't change every few minutes.

</details>

<details><summary><b>Q5.</b> Finance asks which dbt models drive 80% of Snowflake spend. How do you answer by tomorrow?</summary>

Set a `query_tag` per model in dbt-snowflake, then sum `credits_attributed_compute` by `query_tag` in `ACCOUNT_USAGE.QUERY_ATTRIBUTION_HISTORY`. Note that it excludes idle time and has hours of latency, so compare against `WAREHOUSE_METERING_HISTORY` to size the idle waste separately.

</details>

<details><summary><b>Q6.</b> Mini design: 2 TB <code>fct_pings</code>, a dispatch dashboard filters by yesterday and <code>truck_id</code>, and a nightly dbt model rebuilds the table. Layout and warehouse choices?</summary>

- **Layout:** since the table is rebuilt, `order by event_date, truck_id` in the model gives near-perfect pruning with no clustering bill. Better still, make it incremental with `delete+insert` or `microbatch` by date so new data lands in date order.
- **Queries:** use range predicates, not `date(event_ts)`.
- **Warehouses:** dbt on `TRANSFORM_WH`, sized by credits test. Dashboard on a small multi-cluster `BI_WH` with `AUTO_SUSPEND = 60`.
- **Spend:** tag queries per model.

</details>

---

## Further reading
- **[SELECT — Snowflake query optimization](https://select.dev/posts/snowflake-query-optimization)**: a strong external walkthrough of the query profile, pruning, spilling and join explosions.

## Related
- [Warehouse refactor & consolidation](../system_design/warehouse-refactor-consolidation/README.md): applying all of this to an inherited production warehouse
- [Freight billing warehouse](../system_design/freight-billing-warehouse/README.md): greenfield dbt/Snowflake/Airflow design
- [SQL vs NoSQL](../system_design/99-reference/sql-vs-nosql.md): why the warehouse is columnar in the first place
- [sql-advanced.md](sql-advanced.md): dedup with `QUALIFY`, anti-joins, extracting from OLTP
- [databricks.md](databricks.md): the Delta equivalents (file skipping, liquid clustering)
