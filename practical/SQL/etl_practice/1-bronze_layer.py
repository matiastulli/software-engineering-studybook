"""
BRONZE LAYER – Raw Ingestion & Validation
==========================================
Bronze = land exactly what arrived, but catch anything that would corrupt
the rest of the pipeline early.

Rules:
  - Never transform business logic here.
  - Preserve raw data (add audit columns, don't mutate source columns).
  - Quarantine bad records instead of silently dropping them.

Problems this layer catches:
  1. Schema mismatch / unexpected columns
  2. Duplicates in the source file
  3. Required fields that are NULL
  4. Values outside allowed domain (wrong status codes, negative prices, etc.)
  5. Bad date / number formats in manual/CSV uploads
  6. Add audit columns (ingestion timestamp, source file, batch id)
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, DateType

spark = SparkSession.builder \
    .appName("BronzeLayer") \
    .master("local[*]") \
    .getOrCreate()
spark.sparkContext.setLogLevel("WARN")


# ── 0. Expected schema (define once, enforce everywhere) ─────────────────────
# Always declare the schema explicitly. Never infer from CSV — inferred schemas
# silently cast wrong types (e.g. "01" as integer becomes 1, losing the leading zero).

EXPECTED_SCHEMA = StructType([
    StructField("order_id",    StringType(),  nullable=True),
    StructField("customer_id", StringType(),  nullable=True),
    StructField("amount",      DoubleType(),  nullable=True),
    StructField("status",      StringType(),  nullable=True),
    StructField("order_date",  StringType(),  nullable=True),  # string first; cast in Silver
])
# NOTE: all fields are nullable=True here because we are simulating dirty raw input.
# nullable=False in StructType is enforced by Spark at DataFrame creation time,
# which would reject the row before we can even flag it.
# In real ETL, files (CSV/Parquet) are read permissively — NULLs arrive in any column.
# The NULL check for required fields is done explicitly in code (step 4 below).
REQUIRED_FIELDS = ["order_id", "customer_id"]

VALID_STATUSES = {"pending", "completed", "cancelled", "refunded"}


# ── 1. Simulate a raw CSV with problems ──────────────────────────────────────
raw_data = [
    # order_id, customer_id, amount, status,    order_date
    ("ORD001",  "C01",       150.0,  "completed", "2024-01-15"),
    ("ORD002",  "C02",       -50.0,  "completed", "2024-01-16"),   # bad: negative amount
    ("ORD003",  None,        200.0,  "pending",   "2024-01-17"),   # bad: NULL customer_id
    ("ORD001",  "C01",       150.0,  "completed", "2024-01-15"),   # bad: duplicate
    ("ORD004",  "C03",       300.0,  "SHIPPED",   "2024-01-18"),   # bad: invalid status
    ("ORD005",  "C04",       100.0,  "pending",   "not-a-date"),   # bad: malformed date
    ("ORD006",  "C05",       250.0,  "cancelled", "2024-01-20"),   # good
]

raw_df = spark.createDataFrame(raw_data, schema=EXPECTED_SCHEMA)


# ── 2. Add audit columns immediately ─────────────────────────────────────────
# Every bronze record must know WHERE and WHEN it came from.
# In a real job these would come from the job parameters.

raw_df = raw_df \
    .withColumn("_ingested_at",   F.current_timestamp()) \
    .withColumn("_source_file",   F.lit("orders_20240121.csv")) \
    .withColumn("_batch_id",      F.lit("batch_20240121_001"))


# ── 3. Detect duplicates (flag, don't drop — Bronze preserves everything) ────
#
# BAD: silently drop
# raw_df.dropDuplicates(["order_id"])
#
# GOOD: flag with a window function so you can audit how many dupes arrived

from pyspark.sql.window import Window

dedup_window = Window.partitionBy("order_id").orderBy("_ingested_at")

flagged_dupes = raw_df \
    .withColumn("_row_num", F.row_number().over(dedup_window)) \
    .withColumn("_is_duplicate", F.col("_row_num") > 1)

print("=== DUPLICATE DETECTION ===")
flagged_dupes.select("order_id", "customer_id", "_row_num", "_is_duplicate").show()


# ── 4. Validate required fields (NULL check) ─────────────────────────────────
#
# Required columns must not be NULL. Build a single validation flag per row
# so one pass catches all problems.
# We drive this from REQUIRED_FIELDS so adding a new required column is one-line.

validated = flagged_dupes
for col_name in REQUIRED_FIELDS:
    validated = validated.withColumn(
        f"_null_{col_name}",
        F.col(col_name).isNull()
    )


# ── 5. Validate domain values ────────────────────────────────────────────────

validated = validated \
    .withColumn("_invalid_status",
        ~F.lower(F.col("status")).isin(VALID_STATUSES)) \
    .withColumn("_negative_amount",
        F.col("amount") < 0) \
    .withColumn("_bad_date_format",
        F.try_to_date(F.col("order_date"), "yyyy-MM-dd").isNull())


# ── 6. Combine into a single quarantine flag ─────────────────────────────────
#
# A record is quarantined if ANY validation fails.
# Quarantined records go to a dead-letter table, not Silver.

null_flags = [F.col(f"_null_{c}") for c in REQUIRED_FIELDS]
validated = validated.withColumn(
    "_quarantine",
    F.col("_is_duplicate")
    | F.col("_invalid_status")
    | F.col("_negative_amount")
    | F.col("_bad_date_format")
    | F.greatest(*null_flags).cast("boolean")
)

print("=== VALIDATION SUMMARY ===")
null_cols = [f"_null_{c}" for c in REQUIRED_FIELDS]
validated.select(
    "order_id", "customer_id", "amount", "status", "order_date",
    "_is_duplicate", *null_cols, "_invalid_status",
    "_negative_amount", "_bad_date_format", "_quarantine"
).show(truncate=False)


# ── 7. Split: good records → Bronze table, bad records → Dead-letter table ───

good_records = validated.filter(~F.col("_quarantine"))
bad_records  = validated.filter( F.col("_quarantine"))

print(f"Good records : {good_records.count()}")
print(f"Bad records  : {bad_records.count()}")

# In a real pipeline:
# good_records.write.format("delta").mode("append").save("/mnt/bronze/orders")
# bad_records.write.format("delta").mode("append").save("/mnt/bronze/orders_quarantine")


# ── 8. Schema mismatch detection ─────────────────────────────────────────────
#
# If the source file has extra or missing columns, catch it before writing.

def validate_schema(df, expected_schema):
    incoming_cols = set(df.columns)
    expected_cols = set(f.name for f in expected_schema.fields)
    missing  = expected_cols - incoming_cols
    extra    = incoming_cols - expected_cols
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    if extra:
        print(f"WARNING: Unexpected columns (will be dropped): {extra}")
    return df.select([f.name for f in expected_schema.fields])

print("\n=== SCHEMA VALIDATION ===")
# Simulate a file with an extra column
df_with_extra = raw_df.withColumn("unexpected_col", F.lit("oops"))
cleaned = validate_schema(df_with_extra, EXPECTED_SCHEMA)
print("Schema validated. Columns kept:", cleaned.columns)


# ── Interview summary ─────────────────────────────────────────────────────────
print("""
BRONZE LAYER CHECKLIST:
  [ ] Explicit schema — never infer from CSV
  [ ] Audit columns: _ingested_at, _source_file, _batch_id
  [ ] Duplicate detection with ROW_NUMBER (flag, don't drop)
  [ ] NULL check on required fields
  [ ] Domain validation (status codes, ranges, date formats)
  [ ] Single _quarantine flag combining all checks
  [ ] Split into good → bronze table / bad → dead-letter table
  [ ] Schema mismatch detection (missing/extra columns)
""")

spark.stop()
