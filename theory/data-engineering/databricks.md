# Databricks – Interview Study Guide

## TL;DR

- **Databricks is Spark plus Delta Lake on your object storage. Delta adds a transaction log that turns a folder of Parquet into an ACID table.**
- **The `_delta_log` gives you atomic commits, time travel and file-level min/max stats.** Those stats power file skipping, the same idea as Snowflake micro-partition pruning.
- **For new tables, use liquid clustering (`CLUSTER BY`), not partitioning plus Z-order.** Partition only very large tables on a low-cardinality column.
- **Cost ordering, not digits:** Jobs compute < SQL warehouse < all-purpose. Serverless costs more per DBU, but VMs are included and there's no idle time. Never run scheduled jobs on all-purpose clusters.
- **Unity Catalog is governance** (catalog.schema.table grants, row filters, column masks, lineage). **Delta Sharing** shares live tables without copying them.

---

## 1. The problem: a data lake without transactions

Your trucks platform lands **2 TB/day** of Parquet in S3. Plain files on object storage break in predictable ways:

- **Half-written jobs.** A job dies after writing 300 of 500 files, and readers see a partial day.
- **No UPDATE or DELETE.** A GDPR delete or a late invoice correction means rewriting whole folders by hand.
- **Concurrent writers.** Two jobs overwrite the same partition and one silently wins.
- **Slow planning.** Listing millions of files just to plan a query takes minutes.

**Delta Lake** fixes this with a transaction log. That gives the lake the **ACID** guarantees a database has:
- **A**tomic commits: all files or none.
- **C**onsistent schema enforcement.
- **I**solated snapshot reads.
- **D**urable commits in the log.

**Databricks** is the managed platform around it: Spark (plus Photon), Delta, Unity Catalog, jobs and SQL warehouses.

| | Postgres-style DBMS | Databricks lakehouse |
|---|---|---|
| Built for | OLTP: point reads and writes, many small transactions | Analytics: big scans, batch/stream ETL, ML |
| Storage | Proprietary pages on local disk | Open Parquet + Delta log in *your* bucket |
| Compute | Coupled to storage | Separate clusters. Scale out, and pay nothing when idle |

**Decision rule:** app transactions → Postgres. Analytics on lake-scale files with Python/Spark ETL or ML → Databricks. SQL-first warehouse team → see §8.

---

## 2. Delta Lake: how the log works

```
loads/
├── part-0000-a1.parquet
├── part-0001-b2.parquet
└── _delta_log/
    ├── 00000000000000000000.json      ← v0: CREATE
    ├── 00000000000000000001.json      ← v1: add part-0000, part-0001 (with min/max stats per column)
    ├── 00000000000000000002.json      ← v2: MERGE → remove part-0001, add part-0002
    └── 00000000000000000010.checkpoint.parquet   ← periodic snapshot of the log
```

**Mechanism.** Each commit is a JSON file of actions: `add` (file plus stats), `remove`, `metaData` (schema), `protocol` and `commitInfo`. A reader loads the latest checkpoint, replays newer JSONs, and gets the exact file list for that version. Writers use **optimistic concurrency**: write files, then try to create the next version number. If another writer got there first and touched the same files, the commit fails and retries. Readers never block.

**Bridge:** the log's per-file min/max stats are to Delta what micro-partition metadata is to Snowflake. A `WHERE truck_id = 'T-42'` skips every file whose range excludes it.

### Time travel, history, restore

```sql
SELECT * FROM loads VERSION AS OF 41;
SELECT * FROM loads TIMESTAMP AS OF '2026-09-01 06:00';
DESCRIBE HISTORY loads;              -- who, what operation, rows/files changed per version
RESTORE TABLE loads TO VERSION AS OF 41;   -- a NEW commit that re-adds old files; history is kept
```

### VACUUM

`remove` only hides a file logically. `VACUUM` physically deletes unreferenced files older than the retention period (default **7 days**).

```sql
VACUUM loads DRY RUN;
VACUUM loads;                -- default retention
```
**Gotcha:** VACUUM shortens time travel. Once files are gone, `VERSION AS OF` older versions fails. Retention below 7 days needs a safety check disabled, and it can break long-running readers and streams. Don't do it in prod.

### Change Data Feed

`delta.enableChangeDataFeed = true` records row-level inserts, updates and deletes per version, so downstream jobs read *changes* instead of re-scanning. It's the Delta counterpart of a Snowflake Stream.

**Decision rule:** undo a bad write → `RESTORE`. Audit → `DESCRIBE HISTORY`. Incremental downstream → CDF. Schedule `VACUUM` with a retention of at least your time-travel and stream-lag needs.

---

## 3. Data layout: partition vs Z-order vs liquid clustering

**The problem.** Dispatch queries `WHERE truck_id = ? AND event_date BETWEEN …` on a 20 TB pings table. File skipping only works if files hold *narrow* ranges of the filter columns.

| | Hive-style partitioning | `OPTIMIZE … ZORDER BY` | **Liquid clustering** (`CLUSTER BY`) |
|---|---|---|---|
| Mechanism | One folder per value, exact pruning | Rewrites files so nearby values co-locate, then stats skipping | Incremental clustering on keys, then stats skipping |
| Good columns | Low cardinality (date) | High-cardinality filter columns | Any of your common filter columns |
| Change keys later | Full rewrite | Re-run on everything | `ALTER TABLE … CLUSTER BY (…)`, no rewrite of old data |
| Maintenance | Small-file risk if the column is too fine | Full re-Z-order is expensive | `OPTIMIZE` clusters only what's needed; can be automatic |
| Status | Legacy default | Legacy | **Recommended for new tables** |

```sql
CREATE TABLE pings (...) CLUSTER BY (truck_id, event_date);
OPTIMIZE pings;                       -- incremental clustering + compaction
```

Facts (checked 2026-09, Databricks docs):
- Databricks recommends liquid clustering for new tables.
- It's GA for Delta on DBR 15.4 LTS+.
- It **can't be combined** with partitioning or `ZORDER` on the same table.
- Unity Catalog managed tables can hand clustering and `OPTIMIZE`/`VACUUM` to **predictive optimization**, including automatic key selection.

Databricks' own guidance is to **not partition tables under ~1 TB**, and to keep each partition around ≥1 GB. Partitioning pings by `truck_id` gives 100k folders of tiny files, which is the classic small-file problem.

**Bridge:** liquid clustering ≈ Snowflake automatic clustering ≈ Spark `sortWithinPartitions` before a write. They all narrow min/max ranges per file.

**Decision rule:** new table → `CLUSTER BY` your 1–4 most common filter columns. Existing partitioned table that works → leave it, and migrate when keys need to change or small files hurt. Z-order only on legacy tables you can't migrate yet.

---

## 4. Compute and cost

**The problem.** A team runs its nightly 40-minute ETL on the same all-purpose cluster people use for notebooks, with auto-terminate unset. It burns 24 h/day of the most expensive compute type.

**Price model.** `cost = DBUs consumed × $/DBU (by compute type and tier) + cloud VMs` (VMs are included for serverless).

| Compute | For | Relative $/DBU (approx., AWS US, checked 2026-09) |
|---|---|---|
| **Jobs compute** (classic) | Scheduled pipelines. Starts per run, ends after | Lowest (≈ $0.15) |
| **SQL warehouse**: Classic / Pro / Serverless | BI, dbt-on-Databricks, SQL | ≈ $0.22 / ≈ $0.55 / ≈ $0.70 (serverless includes VMs) |
| **All-purpose** | Interactive notebooks, shared dev | High (≈ $0.40–0.55) + VMs |
| **Serverless jobs / notebooks** | No cluster management, fast start | Higher per DBU, VMs included |

Official pricing pages render prices by region and tier dynamically, so these are third-party 2026 figures. **Remember the ordering, not the numbers.**

**Decision rule:**
- **Scheduled ETL** → jobs compute, or serverless jobs if startup time and ops matter more than $/DBU.
- **Exploration** → all-purpose with auto-terminate at 30–60 min.
- **BI and dashboards** → serverless SQL warehouse for bursty use (it stops quickly), Pro for steady all-day load.
- **Streaming or declarative pipelines** → a pipelines-managed cluster (§5).

**Cost levers, in order of impact:**
1. Jobs compute instead of all-purpose for anything scheduled.
2. Auto-terminate and auto-stop everywhere.
3. Spot instances for workers, with an on-demand driver.
4. Fix layout (§3) and shuffles ([pyspark.md](pyspark.md)) so jobs finish sooner. Photon helps scan-heavy SQL, but its DBU rate is higher, so measure.
5. Incremental processing (CDF, streaming tables) instead of full rebuilds.

---

## 5. Pipelines: Structured Streaming, Auto Loader, Lakeflow Declarative Pipelines

- **Structured Streaming.** Spark's stream engine treats a stream as an unbounded table processed in micro-batches. It gets exactly-once into Delta through checkpoints plus transactional commits. Event time, watermarks and delivery semantics are explained in [streaming-tools.md](../system_design/99-reference/streaming-tools.md).
- **Auto Loader** (`cloudFiles`) incrementally picks up new files landing in S3 and tracks which ones it has seen, so you don't list the bucket every run.
- **Lakeflow Declarative Pipelines**, formerly **Delta Live Tables (DLT)** and renamed in 2025 (checked 2026-09, Databricks docs). You declare streaming tables and materialized views. The framework handles dependencies, retries, infrastructure and data-quality **expectations**. Existing DLT code keeps working. The open-source counterpart is Spark Declarative Pipelines.

```python
from pyspark import pipelines as dp          # older code: import dlt

@dp.table
@dp.expect_or_drop("valid_truck", "truck_id IS NOT NULL")
def pings_clean():
    return spark.readStream.table("pings_raw")
```

**Decision rule:** a few custom streaming jobs → Structured Streaming on jobs compute. Many bronze→silver→gold tables with quality rules → Declarative Pipelines. Files arriving in S3 → Auto Loader as the source in both cases.

---

## 6. Governance: Unity Catalog and Delta Sharing

### Unity Catalog

**The problem.** Five workspaces, each with its own Hive metastore and its own grants. Nobody can answer "who can read carrier bank details?"

Unity Catalog is one metastore per region, attached to workspaces:
- **A three-level namespace:** `catalog.schema.table`.
- **Ownership plus privileges.** Object owners and principals with **`MANAGE`** can grant on an object. Admin roles are account admin, metastore admin and workspace admin. There is no separate "data steward" construct.
- **Fine-grained access** through SQL UDFs.
- **Lineage** (table and column level), captured automatically for queries run through UC and queryable in system tables such as `system.access.table_lineage`. Reads of raw paths that bypass the catalog aren't captured.

```sql
GRANT USE CATALOG ON CATALOG prod TO `analysts`;
GRANT USE SCHEMA, SELECT ON SCHEMA prod.billing TO `analysts`;

-- Row filter: carriers see only their own invoices
CREATE FUNCTION prod.billing.carrier_filter(cid INT)
  RETURN is_account_group_member('finance') OR cid = current_carrier_id();  -- current_carrier_id(): your own UDF
ALTER TABLE prod.billing.invoices SET ROW FILTER prod.billing.carrier_filter ON (carrier_id);

-- Column mask: hide bank account except for finance
CREATE FUNCTION prod.billing.mask_iban(v STRING)
  RETURN CASE WHEN is_account_group_member('finance') THEN v ELSE '****' END;
ALTER TABLE prod.billing.carriers ALTER COLUMN iban SET MASK prod.billing.mask_iban;
```

### Delta Sharing

An **open protocol** for sharing live tables. The provider grants a *share* to a *recipient*. The recipient reads the provider's files through short-lived pre-signed URLs, with **no copy and no ETL**. Recipients can be another Databricks workspace (the share shows up as a catalog) or open clients: pandas, Spark, Power BI.

```sql
CREATE SHARE carrier_scorecards;
ALTER SHARE carrier_scorecards ADD TABLE prod.gold.carrier_monthly;
CREATE RECIPIENT acme_logistics;      -- non-Databricks recipients get an activation link
GRANT SELECT ON SHARE carrier_scorecards TO RECIPIENT acme_logistics;
```

**Decision rule:** a partner needs always-fresh tables, revocable and audited → Delta Sharing, not nightly CSV exports to S3. Internal access control → UC grants, with row filters and masks instead of per-audience copied views.

**Also worth naming:** **Photon** is a C++ vectorized engine behind the same APIs. It's on by default in SQL warehouses and speeds scan and aggregation-heavy SQL. **MLflow** handles experiment tracking, model registry and serving.

---

## 7. Failure modes

| Failure | Shows up as | Mitigate |
|---|---|---|
| Small files | Slow planning, thousands of tiny files per table | Optimized writes, auto compaction, `OPTIMIZE`, predictive optimization; never partition by high cardinality |
| Concurrent write conflict | `ConcurrentAppendException` on MERGE | Narrow the MERGE condition to the target partition or cluster range; serialize writers per table |
| VACUUM too aggressive | Time travel or a restarted stream fails with missing files | Retention ≥ longest time-travel and stream-downtime need |
| Idle all-purpose cluster | Monthly bill spike with no job growth | Cluster policies enforcing auto-terminate; jobs compute for schedules |
| Lineage gaps | A table missing from impact analysis | Read and write through UC table names, not raw `s3://` paths |

---

## 8. Databricks vs Snowflake (a fair comparison)

Both have converged a lot. Interviewers want to hear *why you'd pick one for this team*, not a feature war.

| | Databricks | Snowflake |
|---|---|---|
| Heritage | Spark and ETL/ML first, grew into SQL warehousing | SQL warehouse first, grew into Python (Snowpark) and ML |
| Storage | Delta (open) in your bucket; Iceberg readers via UniForm | Managed native format, or **Iceberg tables** in your bucket |
| Streaming | Structured Streaming, Declarative Pipelines: arbitrary stateful logic | **Snowpipe Streaming** (row-level ingest, seconds), Streams + Tasks, **Dynamic Tables** (declarative, target lag). Less suited to custom stateful stream processing |
| Knobs | More (clusters, runtimes, layout), reduced by serverless and predictive optimization | Fewer (warehouse size, multi-cluster, clustering key) |
| Governance | Unity Catalog | Horizon |
| dbt | Supported | Most common pairing |

**Decision rule:**
- **Snowflake** → a SQL-and-dbt team with data already in a warehouse, wanting the fewest knobs.
- **Databricks** → heavy Python/Spark transformations, ML on the same data, lake files as the system of record, or custom streaming.
- **Either** → an open-format requirement (Delta or Iceberg). Choose on team skills and existing platform.

---

## Common wrong answers

- **"Z-order the table and partition by `truck_id`."** High-cardinality partitioning creates the small-file problem. New tables use liquid clustering, which can't be combined with partitions or Z-order anyway.
- **"Snowflake is proprietary and can't stream."** It has Iceberg tables, Snowpipe Streaming and Dynamic Tables. The honest gap is custom stateful stream processing, not ingestion.
- **"Run VACUUM with 0 hours to save storage."** That destroys time travel and breaks running readers and streams. The savings are rarely worth it.
- **"Serverless is always more expensive."** Per DBU, yes. For bursty workloads with VMs included and no idle time, the total is often lower.
- **"DLT is deprecated."** It was renamed to Lakeflow Declarative Pipelines, and existing code still runs.

---

## Self-check

<details><summary><b>Q1.</b> A Spark job writing to plain Parquet dies halfway. What do readers see, and what does Delta change mechanically?</summary>

With plain Parquet, readers see whatever files landed: a partial, inconsistent day. With Delta, new files are invisible until the job atomically writes the next `_delta_log` JSON. No commit means readers still see the previous version, and the orphan files are cleaned later by `VACUUM`.

</details>

<details><summary><b>Q2.</b> New 20 TB pings table, queried by <code>truck_id</code> and date range. Partition, Z-order, or liquid clustering? Why?</summary>

Liquid clustering: `CLUSTER BY (truck_id, event_date)`. It narrows min/max ranges per file so stats-based skipping works on both columns, and keys can change later without a rewrite. Partitioning by `truck_id` would create 100k small-file folders. Z-order is the legacy approach and can't be mixed with liquid clustering.

</details>

<details><summary><b>Q3.</b> Someone ran a bad MERGE on <code>invoices</code> an hour ago. How do you recover, and what could make recovery impossible?</summary>

Use `DESCRIBE HISTORY invoices` to find the version before the MERGE, then `RESTORE TABLE invoices TO VERSION AS OF n`. That creates a new commit and keeps history. It fails if `VACUUM` already deleted the old files, which happens when retention was set shorter than the gap.

</details>

<details><summary><b>Q4.</b> The Databricks bill doubled with no new pipelines. Where do you look first?</summary>

1. Compute usage by type: scheduled jobs running on all-purpose clusters, or clusters without auto-terminate.
2. SQL warehouses without auto-stop.
3. Jobs that got slower from small files or skew, so the same work burns more DBUs.
4. Photon or serverless switched on for workloads that don't benefit.

Enforce auto-terminate and jobs compute through cluster policies.

</details>

<details><summary><b>Q5.</b> A carrier partner wants daily-fresh scorecards for only its own loads. Design the access.</summary>

Build a gold table per carrier scope, or one table with a row filter. Share it through Delta Sharing to that recipient: live, no copies, revocable and audited. Internally, UC grants plus a row filter on `carrier_id`, with a column mask on bank details.

</details>

---

## Related

- [pyspark.md](pyspark.md): shuffles, skew, broadcast joins, reading plans
- [snowflake-performance.md](snowflake-performance.md): the Snowflake equivalents of layout, pruning and cost
- [sql-advanced.md](sql-advanced.md): CDC extraction from Postgres into the lakehouse
- [streaming-tools.md](../system_design/99-reference/streaming-tools.md): delivery semantics, watermarks
- [cloud/architecture-comparison.md](../cloud/architecture-comparison.md): core toolkit and scale ladder
