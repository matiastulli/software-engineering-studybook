"""
GOLD LAYER – Aggregations, Business Metrics & Idempotent Writes
================================================================
Gold = business-ready aggregates and KPIs, optimized for reads.
Input: clean, deduplicated Silver data.

Rules:
  - Aggregations and business logic live here, not Silver.
  - Writes must be IDEMPOTENT — running the pipeline twice must not
    create duplicate rows or double-count metrics.
  - Use MERGE INTO (upsert), not append.
  - Partition and optimize for the query patterns of the consumers.

Problems this layer solves:
  1. Non-idempotent writes (INSERT instead of MERGE → duplicates on retry)
  2. Full reload every run instead of incremental (watermark pattern)
  3. Wrong aggregation due to NULLs not handled upstream
  4. Missing window functions for ranking / running totals
  5. Unoptimized Delta tables (small files, no ZORDER)
  6. No data freshness tracking
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

spark = SparkSession.builder \
    .appName("GoldLayer") \
    .master("local[*]") \
    .getOrCreate()
spark.sparkContext.setLogLevel("WARN")


# ── Simulate clean Silver data ────────────────────────────────────────────────

silver_data = [
    ("ORD001", "C01", "Alice",  "US", 150.00, "completed",  "2024-01-15"),
    ("ORD006", "C05", "Eva",    "FR", 250.00, "cancelled",  "2024-01-20"),
    ("ORD007", "C02", "Bob",    "UK", 300.00, "pending",    "2024-01-22"),
    ("ORD008", "C03", "Carlos", "DE",   0.00, "completed",  "2024-01-23"),
    ("ORD009", "C01", "Alice",  "US", 500.00, "completed",  "2024-01-25"),
    ("ORD010", "C02", "Bob",    "UK", 120.00, "completed",  "2024-02-01"),
    ("ORD011", "C01", "Alice",  "US", 200.00, "completed",  "2024-02-03"),
]

silver_df = spark.createDataFrame(
    silver_data,
    ["order_id", "customer_id", "name", "country", "amount", "status", "order_date"]
).withColumn("order_date", F.to_date("order_date", "yyyy-MM-dd"))


# ── 1. Incremental load with watermark ───────────────────────────────────────
#
# BAD: read ALL silver data every run → re-scans terabytes to compute the same
#      historical metrics over and over.
#
# GOOD: read only rows changed since the last successful run.
#
# The watermark is the MAX order_date (or _silver_updated_at) from the last run.
# Store it in a control table or a simple file.

LAST_WATERMARK = "2024-01-31"   # simulates what you'd read from your control table

incremental_df = silver_df.filter(
    F.col("order_date") > F.lit(LAST_WATERMARK)
)

print(f"=== INCREMENTAL LOAD: rows after {LAST_WATERMARK} ===")
incremental_df.show()


# ── 2. Business aggregations ─────────────────────────────────────────────────

# KPI 1: revenue by country per month
revenue_by_country = (
    silver_df
    .filter(F.col("status") == "completed")     # only count completed orders
    .withColumn("month", F.date_format("order_date", "yyyy-MM"))
    .groupBy("country", "month")
    .agg(
        F.count("order_id").alias("order_count"),
        F.sum("amount").alias("total_revenue"),
        F.avg("amount").alias("avg_order_value"),
    )
)

print("=== KPI: REVENUE BY COUNTRY / MONTH ===")
revenue_by_country.show()


# KPI 2: customer lifetime value with running total (window function)
customer_window = Window.partitionBy("customer_id").orderBy("order_date") \
    .rowsBetween(Window.unboundedPreceding, Window.currentRow)

customer_ltv = (
    silver_df
    .filter(F.col("status") == "completed")
    .withColumn("running_revenue", F.sum("amount").over(customer_window))
    .withColumn("order_rank",      F.row_number().over(
        Window.partitionBy("customer_id").orderBy("order_date")
    ))
)

print("=== KPI: CUSTOMER RUNNING REVENUE ===")
customer_ltv.select("customer_id", "name", "order_date", "amount", "running_revenue", "order_rank").show()


# KPI 3: month-over-month revenue growth (LAG)
monthly_revenue = (
    silver_df
    .filter(F.col("status") == "completed")
    .withColumn("month", F.date_format("order_date", "yyyy-MM"))
    .groupBy("month")
    .agg(F.sum("amount").alias("total_revenue"))
    .orderBy("month")
)

mom_window = Window.orderBy("month")

monthly_growth = monthly_revenue \
    .withColumn("prev_month_revenue", F.lag("total_revenue", 1).over(mom_window)) \
    .withColumn("mom_growth_pct",
        F.round(
            (F.col("total_revenue") - F.col("prev_month_revenue"))
            / F.col("prev_month_revenue") * 100,
            2
        )
    )

print("=== KPI: MONTH-OVER-MONTH GROWTH ===")
monthly_growth.show()


# ── 3. Idempotent write: MERGE INTO (upsert) ─────────────────────────────────
#
# BAD: .write.mode("append") → every pipeline run appends the same rows again.
#      Re-running after a failure doubles all your metrics.
#
# GOOD: MERGE INTO matches on the business key, updates if exists, inserts if not.
#       Running it twice produces the same result as running it once.

# Delta Lake MERGE INTO pattern:
MERGE_SQL = """
MERGE INTO gold.revenue_by_country AS target
USING new_revenue AS source
ON target.country = source.country AND target.month = source.month
WHEN MATCHED THEN
    UPDATE SET
        target.order_count   = source.order_count,
        target.total_revenue = source.total_revenue,
        target.avg_order_value = source.avg_order_value,
        target._updated_at   = current_timestamp()
WHEN NOT MATCHED THEN
    INSERT (country, month, order_count, total_revenue, avg_order_value, _updated_at)
    VALUES (source.country, source.month, source.order_count,
            source.total_revenue, source.avg_order_value, current_timestamp())
"""

# In a real Databricks job you'd run:
# revenue_by_country.createOrReplaceTempView("new_revenue")
# spark.sql(MERGE_SQL)
print("=== MERGE INTO PATTERN (idempotent upsert) ===")
print(MERGE_SQL)


# ── 4. Delta Lake optimization ───────────────────────────────────────────────
#
# After writing, run OPTIMIZE + ZORDER so consumers scan fewer files.
# ZORDER co-locates rows with the same value in fewer files (like a clustered index).
# Run this after every significant write batch, not on every micro-batch.

OPTIMIZE_SQL = """
OPTIMIZE gold.revenue_by_country
ZORDER BY (country, month)
"""

# In Databricks:
# spark.sql(OPTIMIZE_SQL)
print("=== OPTIMIZE + ZORDER (run after bulk writes) ===")
print(OPTIMIZE_SQL)

# VACUUM: remove old Delta files (default 7-day retention).
# Only run after you're sure no reader holds an old snapshot.
VACUUM_SQL = "VACUUM gold.revenue_by_country RETAIN 168 HOURS"
print(f"VACUUM: {VACUUM_SQL}")


# ── 5. Data freshness tracking ───────────────────────────────────────────────
#
# Consumers need to know how stale the Gold data is.
# Write a simple metadata row after each successful run.

freshness_data = [(
    "gold.revenue_by_country",
    "2024-02-03",           # max order_date processed
    "2024-02-04 06:00:00",  # pipeline run time
    "success",
)]
freshness_df = spark.createDataFrame(
    freshness_data,
    ["table_name", "max_event_date", "pipeline_run_at", "status"]
)

print("\n=== DATA FRESHNESS METADATA ===")
freshness_df.show(truncate=False)

# In a real pipeline:
# freshness_df.write.format("delta").mode("append").save("/mnt/gold/_pipeline_log")


# ── 6. Partitioning strategy ─────────────────────────────────────────────────
#
# Partition by the column most queries filter on (usually date).
# BAD: no partitioning → every query scans the whole table.
# BAD: too many partitions (partitionBy("order_id")) → millions of tiny files.
# GOOD: partitionBy("country", "month") if consumers always filter by those.

# In a real write:
# revenue_by_country.write \
#     .format("delta") \
#     .mode("overwrite") \
#     .partitionBy("country", "month") \
#     .option("overwriteSchema", "true") \
#     .save("/mnt/gold/revenue_by_country")


# ── Interview summary ─────────────────────────────────────────────────────────
print("""
GOLD LAYER CHECKLIST:
  [ ] Incremental load with watermark (don't re-scan all history every run)
  [ ] Filter early: only aggregate rows with status = 'completed' etc.
  [ ] MERGE INTO for idempotent writes (not append)
  [ ] Window functions for running totals, rankings, MoM growth
  [ ] OPTIMIZE + ZORDER BY after bulk writes
  [ ] VACUUM after retention period has passed
  [ ] Partition by the column consumers filter on most
  [ ] Write data freshness metadata after each successful run
""")

spark.stop()
