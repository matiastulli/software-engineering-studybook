-- ============================================================
-- SNOWFLAKE: SEMI-STRUCTURED DATA  (VARIANT, FLATTEN)
-- ============================================================
-- Snowflake stores JSON / XML / Avro natively in VARIANT columns.
-- You query nested fields with colon notation: col:field::TYPE
-- This is extremely common in ETL interviews — manual CSV/JSON uploads.
-- ============================================================

USE DATABASE etl_practice;
USE SCHEMA bronze;
USE WAREHOUSE practice_wh;


-- ── 1. Load raw JSON into a VARIANT column ────────────────────
CREATE OR REPLACE TABLE raw_events (
    event_id   INT AUTOINCREMENT,
    raw        VARIANT,
    loaded_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- INSERT using PARSE_JSON to turn a string into VARIANT
INSERT INTO raw_events (raw) SELECT PARSE_JSON('{
    "order_id": "ORD001",
    "customer": { "id": "C01", "name": "Alice", "country": "US" },
    "items": [
        {"sku": "SKU-A", "qty": 2, "price": 29.99},
        {"sku": "SKU-B", "qty": 1, "price": 49.99}
    ],
    "tags": ["vip", "newsletter"],
    "total": 109.97,
    "created_at": "2024-01-15T10:30:00Z"
}');

INSERT INTO raw_events (raw) SELECT PARSE_JSON('{
    "order_id": "ORD002",
    "customer": { "id": "C02", "name": "Bob", "country": "UK" },
    "items": [
        {"sku": "SKU-C", "qty": 3, "price": 15.00}
    ],
    "tags": [],
    "total": 45.00,
    "created_at": "2024-01-16T08:00:00Z"
}');


-- ── 2. Basic field extraction with colon notation ─────────────
-- Syntax: column:path::TYPE
-- Always cast to a concrete type — VARIANT arithmetic is slow.

SELECT
    raw:order_id::STRING                    AS order_id,
    raw:customer.id::STRING                 AS customer_id,
    raw:customer.name::STRING               AS customer_name,
    raw:customer.country::STRING            AS country,
    raw:total::NUMBER(10,2)                 AS total,
    raw:created_at::TIMESTAMP_NTZ           AS created_at
FROM raw_events;


-- ── 3. FLATTEN: explode an array into rows ────────────────────
-- FLATTEN turns each element of a JSON array into its own row.
-- LATERAL join connects each exploded row back to its parent.

-- Explode the 'items' array: one row per item per order
SELECT
    e.raw:order_id::STRING          AS order_id,
    f.value:sku::STRING             AS sku,
    f.value:qty::INT                AS qty,
    f.value:price::NUMBER(10,2)     AS unit_price,
    f.value:qty::INT
        * f.value:price::NUMBER(10,2) AS line_total,
    f.index                         AS item_position   -- 0-based position in array
FROM raw_events e,
LATERAL FLATTEN(input => e.raw:items) f;


-- ── 4. FLATTEN a flat array (tags) ───────────────────────────
SELECT
    e.raw:order_id::STRING   AS order_id,
    f.value::STRING          AS tag
FROM raw_events e,
LATERAL FLATTEN(input => e.raw:tags) f;

-- Orders with NO tags: outer => true keeps empty arrays as one NULL row
SELECT
    e.raw:order_id::STRING   AS order_id,
    f.value::STRING          AS tag
FROM raw_events e,
LATERAL FLATTEN(input => e.raw:tags, outer => true) f;


-- ── 5. FLATTEN with PATH for deeply nested keys ───────────────
-- path shortcuts directly into nested objects
SELECT
    e.raw:order_id::STRING      AS order_id,
    f.key                       AS field_name,
    f.value::STRING             AS field_value
FROM raw_events e,
LATERAL FLATTEN(input => e.raw:customer) f;


-- ── 6. Build a Silver table from the raw JSON ─────────────────
-- Flatten in a single INSERT SELECT — one row per order line item.

CREATE OR REPLACE TABLE silver.order_items AS
SELECT
    e.raw:order_id::STRING              AS order_id,
    e.raw:customer.id::STRING           AS customer_id,
    e.raw:customer.country::STRING      AS country,
    f.value:sku::STRING                 AS sku,
    f.value:qty::INT                    AS qty,
    f.value:price::NUMBER(10,2)         AS unit_price,
    f.value:qty::INT
        * f.value:price::NUMBER(10,2)   AS line_total,
    e.raw:created_at::TIMESTAMP_NTZ     AS order_created_at,
    e.loaded_at                         AS _loaded_at
FROM raw_events e,
LATERAL FLATTEN(input => e.raw:items) f;

SELECT * FROM silver.order_items;


-- ── 7. TYPEOF and handling missing keys ──────────────────────
-- TYPEOF tells you the actual type stored in a VARIANT slot.
-- Accessing a missing key returns NULL (no error).

SELECT
    raw:order_id::STRING            AS order_id,
    TYPEOF(raw:total)               AS total_type,      -- → 'REAL'
    TYPEOF(raw:customer)            AS customer_type,   -- → 'OBJECT'
    TYPEOF(raw:items)               AS items_type,      -- → 'ARRAY'
    raw:nonexistent_field::STRING   AS missing_key      -- → NULL, no error
FROM raw_events;


-- ── 8. IS_OBJECT / IS_ARRAY / IS_NULL_VALUE guards ───────────
-- Use before FLATTEN when the field might not always be an array.

SELECT *
FROM raw_events e,
LATERAL FLATTEN(input => e.raw:items)
WHERE IS_ARRAY(e.raw:items);   -- skip rows where 'items' is not an array


-- ── INTERVIEW SUMMARY ─────────────────────────────────────────
-- Q: How do you query a nested JSON field?
-- A: raw:field.subfield::TYPE  — always cast or results stay VARIANT.
--
-- Q: How do you explode a JSON array?
-- A: LATERAL FLATTEN(input => col:array_field)
--    Each element becomes a row; use f.value to access the element.
--
-- Q: What does outer => true do in FLATTEN?
-- A: Keeps rows where the array is empty or NULL (like a LEFT JOIN).
--    Without it, rows with empty arrays are dropped silently.
--
-- Q: What type should you store raw JSON in Snowflake?
-- A: VARIANT. Max 16 MB per value. Cast to concrete types at query time
--    or during Silver transformation — never leave VARIANT in Gold.
