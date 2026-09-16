-- ============================================================
-- SNOWFLAKE: PERFORMANCE & COST OPTIMIZATION
-- ============================================================
-- Snowflake has NO indexes. Performance comes from:
--   1. Micro-partition pruning (automatic + clustering keys)
--   2. Choosing the right warehouse size
--   3. Avoiding full table scans (result cache, warehouse cache)
--   4. Writing efficient queries (avoid DISTINCT on large sets, etc.)
-- ============================================================

USE DATABASE etl_practice;
USE SCHEMA silver;
USE WAREHOUSE practice_wh;


-- ── 1. MICRO-PARTITIONS & PRUNING ────────────────────────────
-- Snowflake stores data in micro-partitions of ~16 MB compressed.
-- Each partition stores MIN/MAX metadata for every column.
-- A query with WHERE order_date = '2024-01-15' skips all partitions
-- whose MIN/MAX range doesn't include that date — this is pruning.
--
-- After running a query, check partitions scanned vs total:
-- Query Profile → TableScan node → "Partitions scanned / total"
-- If scanned ≈ total → poor pruning → consider a clustering key.


-- ── 2. CLUSTERING KEYS ───────────────────────────────────────
-- When a table is large (hundreds of GB+) and queries always filter
-- on the same column(s), a clustering key re-orders micro-partitions
-- so those filters prune aggressively.
--
-- Good candidates: date columns, region/country, status (low-ish cardinality)
-- Bad candidates: order_id (too high cardinality → useless pruning)

-- Add a clustering key (runs in background, uses credits)
ALTER TABLE silver.orders CLUSTER BY (updated_at::DATE);

-- Check clustering depth (lower = better, 1.0 is perfect)
SELECT SYSTEM$CLUSTERING_INFORMATION('silver.orders', '(updated_at::DATE)');

-- Remove clustering key (stops Automatic Clustering, which costs money)
ALTER TABLE silver.orders DROP CLUSTERING KEY;


-- ── 3. THREE CACHE LAYERS ────────────────────────────────────
-- Layer 1: RESULT CACHE (free, 24 hours)
--   Identical query on unchanged data → served from cache instantly.
--   No warehouse needed. Zero credits.
--   Invalidated when the underlying table changes.
--
-- Layer 2: WAREHOUSE CACHE (local SSD on the warehouse nodes)
--   Data read by a query is cached on the warehouse's local disk.
--   Subsequent queries on the same data hit local disk, not remote storage.
--   Lost when warehouse suspends — this is why AUTO_SUSPEND matters.
--
-- Layer 3: REMOTE STORAGE (S3/Azure/GCS)
--   Always available, always costs a little I/O.

-- Demo: run the same query twice, compare execution time
SELECT country, SUM(amount) FROM silver.orders GROUP BY country;
-- Run again → should be near 0ms (result cache hit)

-- Force bypass the result cache (useful for benchmarking)
ALTER SESSION SET USE_CACHED_RESULT = FALSE;
SELECT country, SUM(amount) FROM silver.orders GROUP BY country;
ALTER SESSION SET USE_CACHED_RESULT = TRUE;  -- reset


-- ── 4. WAREHOUSE SIZING: scale UP vs scale OUT ───────────────
-- Scale UP (bigger warehouse): more CPU/memory per query.
--   → Use for: complex queries, large joins, heavy transformations.
--   Credits double with each size: XS=1, S=2, M=4, L=8, XL=16 per hour.
--
-- Scale OUT (multi-cluster warehouse): more warehouses in parallel.
--   → Use for: many concurrent users/queries hitting the same warehouse.
--   Each additional cluster = same credits as the base cluster.
--
-- Rule: if ONE query is slow → scale up.
--       if MANY queries queue up → scale out.

CREATE OR REPLACE WAREHOUSE practice_wh
    WAREHOUSE_SIZE   = 'X-SMALL'
    AUTO_SUSPEND     = 60
    AUTO_RESUME      = TRUE
    MIN_CLUSTER_COUNT = 1
    MAX_CLUSTER_COUNT = 3       -- auto-scales to 3 clusters under load
    SCALING_POLICY   = 'ECONOMY';  -- ECONOMY = fill clusters before adding new ones
                                   -- STANDARD = add clusters immediately on queuing

-- Temporarily resize for a heavy batch job
ALTER WAREHOUSE practice_wh SET WAREHOUSE_SIZE = 'LARGE';
-- ... run your heavy transformation ...
ALTER WAREHOUSE practice_wh SET WAREHOUSE_SIZE = 'X-SMALL';  -- scale back down


-- ── 5. QUERY OPTIMIZATION PATTERNS ──────────────────────────

-- BAD: SELECT * wastes I/O in columnar storage
SELECT * FROM silver.orders WHERE status = 'completed';

-- GOOD: select only what you need
SELECT order_id, customer_id, amount FROM silver.orders WHERE status = 'completed';

-- BAD: non-sargable filter (function on column prevents pruning)
SELECT * FROM silver.orders WHERE YEAR(updated_at) = 2024;

-- GOOD: range scan enables micro-partition pruning
SELECT * FROM silver.orders
WHERE updated_at >= '2024-01-01' AND updated_at < '2025-01-01';

-- BAD: DISTINCT on a huge result set (full sort pass)
SELECT DISTINCT customer_id FROM silver.orders;

-- GOOD: if you just need existence, EXISTS is cheaper
SELECT c.customer_id
FROM customers c
WHERE EXISTS (SELECT 1 FROM silver.orders o WHERE o.customer_id = c.customer_id);

-- BAD: correlated subquery runs once per row
SELECT order_id,
       (SELECT name FROM customers c WHERE c.customer_id = o.customer_id) AS name
FROM silver.orders o;

-- GOOD: JOIN (executes once, then hash lookup)
SELECT o.order_id, c.name
FROM silver.orders o
JOIN customers c ON o.customer_id = c.customer_id;


-- ── 6. ZERO-COPY CLONING ─────────────────────────────────────
-- Creates an instant copy that shares the same underlying storage.
-- The clone only stores NEW writes — no data duplication at creation time.
-- Extremely useful for dev/test environments and before risky migrations.

-- Clone a table (instant, no storage cost until you write to the clone)
CREATE TABLE silver.orders_backup CLONE silver.orders;

-- Clone at a point in time (Time Travel must be active)
CREATE TABLE silver.orders_before_migration
    CLONE silver.orders
    AT (TIMESTAMP => DATEADD('hour', -2, CURRENT_TIMESTAMP()));

-- Clone an entire database (for a full dev environment)
-- CREATE DATABASE etl_practice_dev CLONE etl_practice;


-- ── 7. TIME TRAVEL ────────────────────────────────────────────
-- Query historical data without restoring a backup.
-- Default retention: 1 day (standard edition), up to 90 days (enterprise).

-- Query data as it was 1 hour ago
SELECT * FROM silver.orders
AT (OFFSET => -3600);           -- seconds

-- Query data before a specific timestamp
SELECT * FROM silver.orders
AT (TIMESTAMP => '2024-01-15 08:00:00'::TIMESTAMP_NTZ);

-- Query data before a specific query ran (get the query_id from query history)
SELECT * FROM silver.orders
BEFORE (STATEMENT => '<query_id_here>');

-- Restore a dropped table (within retention period)
-- DROP TABLE silver.orders;
-- UNDROP TABLE silver.orders;

-- Change retention period per table
ALTER TABLE silver.orders SET DATA_RETENTION_TIME_IN_DAYS = 7;


-- ── 8. COST MONITORING ───────────────────────────────────────

-- Credits used by warehouse per day
SELECT warehouse_name,
       DATE_TRUNC('day', start_time) AS usage_date,
       SUM(credits_used)             AS total_credits
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE start_time >= DATEADD('day', -7, CURRENT_TIMESTAMP())
GROUP BY 1, 2
ORDER BY 2 DESC, 3 DESC;

-- Most expensive queries (by credits scanned)
SELECT query_id, query_text, warehouse_name,
       total_elapsed_time / 1000        AS elapsed_sec,
       bytes_scanned / 1e9              AS gb_scanned,
       partitions_scanned,
       partitions_total,
       ROUND(partitions_scanned * 100.0
             / NULLIF(partitions_total, 0), 1) AS pct_partitions_scanned
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE start_time >= DATEADD('day', -1, CURRENT_TIMESTAMP())
  AND warehouse_name = 'PRACTICE_WH'
ORDER BY bytes_scanned DESC
LIMIT 20;

-- ── INTERVIEW SUMMARY ─────────────────────────────────────────
-- Q: Snowflake has no indexes. How do you speed up queries?
-- A: Micro-partition pruning is automatic. For large tables with repeated
--    filter patterns, add a CLUSTERING KEY on those columns. Also check
--    result cache (same query hits cache), and avoid non-sargable filters.
--
-- Q: When do you scale UP vs scale OUT?
-- A: Scale UP = one slow query needing more CPU/memory.
--    Scale OUT = many concurrent queries queuing up (multi-cluster).
--
-- Q: What is zero-copy cloning?
-- A: An instant snapshot of a table/schema/database that shares storage
--    with the original. Only new writes to the clone consume new storage.
--    Used for dev/test environments and pre-migration safety copies.
--
-- Q: What is the result cache?
-- A: Snowflake caches query results for 24 hours. An identical query on
--    unchanged data returns instantly with zero credits consumed.
