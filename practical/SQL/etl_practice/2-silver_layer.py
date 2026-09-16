"""
SILVER LAYER – Cleaning, Deduplication & Enrichment
=====================================================
Silver = clean, typed, deduplicated, enriched data.
Input: good records from Bronze (quarantine already removed).

Rules:
  - Fix types (cast strings to dates, ints, etc.)
  - Deduplicate — keep only the canonical version of each record.
  - Standardize formats (trim whitespace, lowercase status, etc.)
  - Enrich with lookups (join to dimension tables).
  - Apply business rules (but no aggregations — that's Gold).
  - Still row-level: one source row → one or zero Silver rows.

Problems this layer solves:
  1. String columns that should be typed (date, decimal, boolean)
  2. Leftover duplicates across batches (not just within one file)
  3. Inconsistent string formats (leading spaces, mixed case)
  4. NULLs that need a default / need to be rejected
  5. Enrichment joins that silently drop rows (wrong join type)
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

spark = SparkSession.builder \
    .appName("SilverLayer") \
    .master("local[*]") \
    .getOrCreate()
spark.sparkContext.setLogLevel("WARN")


# ── Simulate clean Bronze output (already passed quarantine) ─────────────────

bronze_data = [
    ("ORD001", "C01", 150.0,  "completed", "2024-01-15", "2024-01-21 08:00:00"),
    ("ORD006", "C05", 250.0,  "CANCELLED", "2024-01-20", "2024-01-21 08:00:00"),  # mixed case
    ("ORD007", "C02", 300.0,  " pending ", "2024-01-22", "2024-01-21 08:00:00"),  # leading spaces
    ("ORD008", "C03", None,   "completed", "2024-01-23", "2024-01-21 08:00:00"),  # NULL amount
    # ORD001 arrives again in the next batch (late-arriving duplicate)
    ("ORD001", "C01", 150.0,  "completed", "2024-01-15", "2024-01-22 09:00:00"),
]

bronze_df = spark.createDataFrame(
    bronze_data,
    ["order_id", "customer_id", "amount", "status", "order_date", "_ingested_at"]
)

# Customers lookup (dimension table)
customers_data = [
    ("C01", "Alice",   "US"),
    ("C02", "Bob",     "UK"),
    ("C03", "Carlos",  "DE"),
    ("C05", "Eva",     "FR"),
    # C04 is missing — intentional to demo join problem
]
customers_df = spark.createDataFrame(customers_data, ["customer_id", "name", "country"])


# ── 1. Type casting ──────────────────────────────────────────────────────────
#
# BAD: leave order_date as string → all downstream date math is broken
# GOOD: cast once in Silver, fail loudly if the cast returns NULL

typed_df = bronze_df \
    .withColumn("order_date",
        F.to_date(F.col("order_date"), "yyyy-MM-dd")) \
    .withColumn("amount",
        F.col("amount").cast("decimal(18,2)"))

# Catch silent cast failures (to_date returns NULL on bad input)
cast_failures = typed_df.filter(
    F.col("order_date").isNull() & F.col("order_date").isNotNull()  # original was not null
)
# In practice: raise an alert or route to quarantine if cast_failures.count() > 0


# ── 2. String standardization ────────────────────────────────────────────────
#
# Trim whitespace and lowercase status so downstream GROUP BY / joins work.
# "CANCELLED" and " pending " and "Pending" must all become "pending".

cleaned_df = typed_df \
    .withColumn("status",
        F.lower(F.trim(F.col("status")))) \
    .withColumn("customer_id",
        F.trim(F.col("customer_id")))

print("=== AFTER STRING STANDARDIZATION ===")
cleaned_df.select("order_id", "status", "customer_id").show()


# ── 3. NULL handling ─────────────────────────────────────────────────────────
#
# Two strategies — pick based on business rules:
#   a) Fill with a default (amount → 0.0 if NULL means "no charge")
#   b) Reject the record (amount → NULL means "data error")
#
# BAD: silently leave NULLs → SUM(amount) returns wrong totals in Gold

cleaned_df = cleaned_df \
    .withColumn("amount",
        F.coalesce(F.col("amount"), F.lit(0.0)))  # business rule: NULL = no charge


# ── 4. Cross-batch deduplication ─────────────────────────────────────────────
#
# Bronze flags duplicates within one file. Silver must also handle the same
# order_id arriving in two different batches (late re-delivery, retry, etc.).
#
# Strategy: keep the record with the LATEST _ingested_at for each order_id.
#
# BAD: dropDuplicates(["order_id"]) — picks an arbitrary row, not the latest

dedup_window = Window.partitionBy("order_id").orderBy(F.col("_ingested_at").desc())

deduped_df = cleaned_df \
    .withColumn("_rank", F.row_number().over(dedup_window)) \
    .filter(F.col("_rank") == 1) \
    .drop("_rank", "_ingested_at")

print("=== AFTER CROSS-BATCH DEDUPLICATION ===")
print(f"Before dedup: {cleaned_df.count()} rows")
print(f"After  dedup: {deduped_df.count()} rows")
deduped_df.show()


# ── 5. Enrichment join — use LEFT JOIN, then audit unmatched rows ─────────────
#
# BAD: INNER JOIN — silently drops orders for customers not in the dimension table.
#      You'll never know ORD008 (C03) dropped; the Gold totals will be wrong.
#
# GOOD: LEFT JOIN — keep all orders, then explicitly flag/investigate the gaps.

enriched_df = deduped_df.join(
    F.broadcast(customers_df),   # small dimension → always broadcast
    on="customer_id",
    how="left"                   # keeps all orders even if customer is missing
)

# Audit: how many orders have no matching customer?
unmatched = enriched_df.filter(F.col("name").isNull())
print(f"\n=== ENRICHMENT AUDIT: {unmatched.count()} orders with no matching customer ===")
unmatched.select("order_id", "customer_id").show()

# In a real pipeline: route unmatched to a reconciliation table or alert.


# ── 6. Add Silver metadata column ────────────────────────────────────────────

silver_df = enriched_df \
    .withColumn("_silver_updated_at", F.current_timestamp())

print("=== FINAL SILVER OUTPUT ===")
silver_df.show(truncate=False)

# In a real pipeline:
# silver_df.write.format("delta").mode("overwrite").option("overwriteSchema","true") \
#     .partitionBy("order_date") \
#     .save("/mnt/silver/orders")


# ── Interview summary ─────────────────────────────────────────────────────────
print("""
SILVER LAYER CHECKLIST:
  [ ] Cast all strings to proper types (date, decimal, boolean)
  [ ] Detect silent cast failures (to_date / cast returning NULL)
  [ ] Trim + lowercase strings before any join or group by
  [ ] COALESCE NULLs with a business-rule default (or reject)
  [ ] Cross-batch dedup with ROW_NUMBER + _ingested_at DESC, not dropDuplicates
  [ ] Always LEFT JOIN to dimension tables, then audit unmatched rows
  [ ] Broadcast small dimension tables (F.broadcast)
  [ ] Add _silver_updated_at audit column
""")

spark.stop()
