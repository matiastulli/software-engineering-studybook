-- ============================================================
-- SNOWFLAKE: STREAMS + TASKS  (CDC pipeline)
-- ============================================================
-- Run each block in order in Snowsight.
-- A Stream captures row-level changes (INSERT/UPDATE/DELETE).
-- A Task consumes the stream on a schedule using MERGE INTO.
-- This is Snowflake's native CDC pattern — interviewers love it.
-- ============================================================


-- ── SETUP ────────────────────────────────────────────────────
USE ROLE SYSADMIN;
CREATE DATABASE IF NOT EXISTS etl_practice;
USE DATABASE etl_practice;
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
USE SCHEMA bronze;

CREATE WAREHOUSE IF NOT EXISTS practice_wh
    WAREHOUSE_SIZE = 'X-SMALL'
    AUTO_SUSPEND   = 60          -- suspend after 60s idle (saves credits)
    AUTO_RESUME    = TRUE;
USE WAREHOUSE practice_wh;


-- ── 1. Source table (simulates an OLTP table we ingest from) ──
CREATE OR REPLACE TABLE bronze.orders (
    order_id     INT,
    customer_id  INT,
    amount       NUMBER(10,2),
    status       VARCHAR(20),
    updated_at   TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ── 2. Create a STREAM on the source table ────────────────────
-- The stream records every INSERT / UPDATE / DELETE that happens
-- after this point. It adds 3 metadata columns:
--   METADATA$ACTION    → 'INSERT' or 'DELETE'
--   METADATA$ISUPDATE  → TRUE if this row is part of an UPDATE pair
--   METADATA$ROW_ID    → unique row identifier
CREATE OR REPLACE STREAM bronze.orders_stream
    ON TABLE bronze.orders
    APPEND_ONLY = FALSE;  -- FALSE = capture updates + deletes too

-- ── 3. Target (clean Silver table) ───────────────────────────
CREATE OR REPLACE TABLE silver.orders (
    order_id    INT PRIMARY KEY,
    customer_id INT,
    amount      NUMBER(10,2),
    status      VARCHAR(20),
    updated_at  TIMESTAMP_NTZ,
    _silver_loaded_at TIMESTAMP_NTZ
);

-- ── 4. Task: consume the stream every 5 minutes ──────────────
-- The MERGE handles INSERT, UPDATE, and DELETE from the stream.
-- SYSTEM$STREAM_HAS_DATA avoids running when stream is empty.
CREATE OR REPLACE TASK silver.process_orders_task
    WAREHOUSE = practice_wh
    SCHEDULE  = '5 MINUTE'
    WHEN SYSTEM$STREAM_HAS_DATA('bronze.orders_stream')   -- skip empty runs
AS
MERGE INTO silver.orders AS tgt
USING (
    -- For updates Snowflake emits a DELETE + INSERT pair.
    -- We keep only the INSERT side (the new value).
    SELECT order_id, customer_id, amount, status, updated_at,
           METADATA$ACTION    AS action,
           METADATA$ISUPDATE  AS is_update
    FROM bronze.orders_stream
) AS src
ON tgt.order_id = src.order_id
WHEN MATCHED AND src.action = 'DELETE' AND NOT src.is_update
    THEN DELETE
WHEN MATCHED AND src.action = 'INSERT'
    THEN UPDATE SET
        tgt.customer_id       = src.customer_id,
        tgt.amount            = src.amount,
        tgt.status            = src.status,
        tgt.updated_at        = src.updated_at,
        tgt._silver_loaded_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED AND src.action = 'INSERT'
    THEN INSERT (order_id, customer_id, amount, status, updated_at, _silver_loaded_at)
    VALUES (src.order_id, src.customer_id, src.amount, src.status,
            src.updated_at, CURRENT_TIMESTAMP());

-- Tasks are created SUSPENDED by default — must resume explicitly.
ALTER TASK silver.process_orders_task RESUME;


-- ── 5. TEST IT ────────────────────────────────────────────────

-- Insert rows → stream captures them
INSERT INTO bronze.orders VALUES
    (1, 101, 150.00, 'pending',   CURRENT_TIMESTAMP()),
    (2, 102, 300.00, 'pending',   CURRENT_TIMESTAMP()),
    (3, 103,  75.50, 'completed', CURRENT_TIMESTAMP());

-- Check the stream: you should see 3 INSERT rows
SELECT *, METADATA$ACTION, METADATA$ISUPDATE FROM bronze.orders_stream;

-- Manually execute the task instead of waiting 5 minutes
EXECUTE TASK silver.process_orders_task;

-- Silver should now have 3 rows
SELECT * FROM silver.orders;

-- Update a row → stream captures DELETE (old) + INSERT (new)
UPDATE bronze.orders SET status = 'completed', updated_at = CURRENT_TIMESTAMP()
WHERE order_id = 1;

-- Stream now has 2 rows for order_id=1: one DELETE, one INSERT
SELECT *, METADATA$ACTION, METADATA$ISUPDATE FROM bronze.orders_stream;

EXECUTE TASK silver.process_orders_task;
SELECT * FROM silver.orders ORDER BY order_id;  -- order_id=1 should be 'completed'

-- Delete a row → stream captures it
DELETE FROM bronze.orders WHERE order_id = 3;
EXECUTE TASK silver.process_orders_task;
SELECT * FROM silver.orders;  -- order_id=3 should be gone

-- Check task run history (did it succeed or fail?)
SELECT *
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
    TASK_NAME => 'PROCESS_ORDERS_TASK',
    SCHEDULED_TIME_RANGE_START => DATEADD('hour', -1, CURRENT_TIMESTAMP())
))
ORDER BY SCHEDULED_TIME DESC;


-- ── 6. TASK TREES (chaining tasks) ───────────────────────────
-- Tasks can depend on each other, forming a DAG.
-- The root task triggers child tasks after it completes.

CREATE OR REPLACE TASK silver.notify_downstream_task
    WAREHOUSE = practice_wh
    AFTER silver.process_orders_task           -- runs after parent finishes
AS
    INSERT INTO silver.pipeline_log(step, logged_at)
    VALUES ('orders_processed', CURRENT_TIMESTAMP());

-- Resume the child too
ALTER TASK silver.notify_downstream_task RESUME;

-- ── INTERVIEW SUMMARY ─────────────────────────────────────────
-- Q: What is a Snowflake Stream?
-- A: A change-tracking object that records INSERT/UPDATE/DELETE on a table
--    since the last time the stream was consumed. Once consumed (via DML),
--    the offset advances. Metadata columns: METADATA$ACTION, METADATA$ISUPDATE.
--
-- Q: How does UPDATE appear in a stream?
-- A: As two rows: a DELETE of the old value + an INSERT of the new value.
--    Filter with METADATA$ISUPDATE = TRUE to distinguish from a true delete.
--
-- Q: What happens if a Task fails?
-- A: The stream offset does NOT advance — data is not lost.
--    The next run picks up the same changes. Check TASK_HISTORY for errors.
--
-- Q: APPEND_ONLY = TRUE vs FALSE?
-- A: TRUE = only captures INSERTs (cheaper, good for append-only sources).
--    FALSE = captures INSERT + UPDATE + DELETE (needed for full CDC).
