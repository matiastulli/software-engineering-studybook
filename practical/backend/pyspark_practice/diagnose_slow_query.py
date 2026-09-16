"""
Diagnosing Slow PySpark Queries – Practical Demo
=================================================
While this script runs, open http://localhost:4040 in your browser to follow
along in the Spark UI.

This script creates 3 classic performance problems on purpose, shows how to
spot each one, then fixes it.

  Problem 1 – Too many shuffle partitions for small data
  Problem 2 – A join that should be broadcast but isn't (SortMergeJoin)
  Problem 3 – Data skew: one task does 90% of the work

Run:
    python diagnose_slow_query.py
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
import time

# ── spark session ────────────────────────────────────────────────────────────
# We intentionally set shuffle.partitions=200 (the default) so Problem 1 is
# visible. We will fix it later in the script.
spark = SparkSession.builder \
    .appName("DiagnoseSlowQuery") \
    .master("local[*]") \
    .config("spark.sql.shuffle.partitions", "200") \
    .config("spark.sql.adaptive.enabled", "false") \
    .getOrCreate()

# Suppress the wall of INFO logs so our print statements are readable
spark.sparkContext.setLogLevel("WARN")


# ── helpers ──────────────────────────────────────────────────────────────────
def banner(title):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")

def run(label, df):
    """Trigger an action, measure time, print result + expose Spark Job ID."""

    print(f"\n>>> {label}")

    sc = spark.sparkContext

    # label the job
    sc.setJobGroup(label, label)
    sc.setLocalProperty("spark.job.description", label)

    t = time.time()

    df.show(5, truncate=False)

    elapsed = time.time() - t

    # fetch jobs created under this group
    job_ids = sc.statusTracker().getJobIdsForGroup(label)

    print(f"    Spark Job IDs: {list(job_ids)}")
    print(f"    completed in {elapsed:.2f}s")

    # cleanup (PySpark way)
    sc.setLocalProperty("spark.job.description", None)
    sc.setJobGroup("", "")

    return elapsed


# ── generate data ────────────────────────────────────────────────────────────
banner("Generating synthetic data")

# Orders table: 300 000 rows, country column is SKEWED (90 % = "US")
orders = spark.range(0, 300_000).select(
    F.col("id").alias("order_id"),
    F.when(F.rand(seed=42) < 0.90, F.lit("US"))
     .when(F.rand(seed=1)  < 0.95, F.lit("UK"))
     .when(F.rand(seed=2)  < 0.98, F.lit("DE"))
     .otherwise(F.lit("FR"))
     .alias("country"),
    (F.rand(seed=3) * 1000).alias("amount"),
)
orders.cache()
orders.count()   # materialise the cache now so timing below is fair
print("orders table ready  (300 000 rows, country is 90 % US)")

# Countries lookup: only 4 rows  ← this is the "small table" for Problem 2
countries = spark.createDataFrame(
    [("US", "United States"), ("UK", "United Kingdom"),
     ("DE", "Germany"),       ("FR", "France")],
    ["code", "country_name"],
)
print("countries table ready  (4 rows)")


# ═══════════════════════════════════════════════════════════════════════════════
# PROBLEM 1 – Too many shuffle partitions for small data
# ═══════════════════════════════════════════════════════════════════════════════
banner("PROBLEM 1 – Too many shuffle partitions (default = 200)")

print("""
WHAT TO LOOK FOR IN SPARK UI  ->  http://localhost:4040
  1. Click the Jobs tab -> find the job triggered below.
  2. Click the job -> click the Stage that says "Exchange" (the shuffle stage).
  3. Click that stage -> scroll to the Task table at the bottom.
  4. You will see 200 tasks listed.
  5. Most tasks show "0 records" and finish in < 1ms -- they are EMPTY.
  6. Only a few tasks have actual data.
  This is wasted overhead: Spark spins up 200 tasks when 4 country groups exist.
""")

bad_q1 = orders.groupBy("country").agg(F.sum("amount").alias("total"))

# explain() prints the physical plan in the terminal.
# Look for: Exchange hashpartitioning(country, 200)
# That "200" is your shuffle.partitions value -- way too many for 4 groups.
print("--- explain() output for the BAD query ---")
bad_q1.explain()
run("BAD groupBy with 200 shuffle partitions", bad_q1)

# FIX: set shuffle.partitions to something small for this dataset
print("\n--- FIX: lower shuffle.partitions to 8 ---")
spark.conf.set("spark.sql.shuffle.partitions", "8")

good_q1 = orders.groupBy("country").agg(F.sum("amount").alias("total"))
print("--- explain() for FIXED query (same plan, fewer partitions) ---")
good_q1.explain()
run("FIXED groupBy with 8 shuffle partitions", good_q1)

print("""
WHY THIS MATTERS:
  200 shuffle partitions is fine for a 10 TB table.
  For a 300k-row table it creates 196 empty tasks = pure overhead.
  Rule of thumb: shuffle.partitions ~ 2-4x the number of CPU cores,
  or tune so each output partition is ~128 MB.
""")


# ═══════════════════════════════════════════════════════════════════════════════
# PROBLEM 2 – SortMergeJoin when a BroadcastHashJoin would be much faster
# ═══════════════════════════════════════════════════════════════════════════════
banner("PROBLEM 2 – Expensive SortMergeJoin instead of BroadcastHashJoin")

# Force Spark to NOT broadcast even tiny tables so we can show the bad plan
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "-1")

print("""
WHAT TO LOOK FOR IN SPARK UI:
  1. Run the BAD join below -> go to SQL/DataFrame tab -> click the query.
  2. In the plan graph you will see:  SortMergeJoin
  3. Above it you will see TWO "Exchange" boxes (one per side of the join).
  4. That means BOTH tables were shuffled across the network before joining.
  Shuffling a 4-row countries table across the network is completely unnecessary.
""")

bad_q2 = orders.join(countries, orders.country == countries.code, "left")
print("--- explain() for BAD join (look for SortMergeJoin + two Exchange nodes) ---")
bad_q2.explain()
run("BAD join -- SortMergeJoin", bad_q2.select("order_id", "country_name", "amount"))

# NOTE: auto-broadcast (re-enabling the threshold) only works when Spark can
# estimate the table's size -- which it can for files (Parquet, Delta) but NOT
# for DataFrames created with createDataFrame() in memory.
# The explicit broadcast() hint always works regardless.

print("\n--- FIX: force broadcast with F.broadcast() hint ---")
print("    This always works. Spark sends 'countries' to every executor in memory.")
good_q2b = orders.join(F.broadcast(countries), orders.country == countries.code, "left")
print("--- explain() for FIXED join (look for BroadcastHashJoin, one Exchange disappears) ---")
good_q2b.explain()
run("FIXED join -- BroadcastHashJoin (explicit hint)", good_q2b.select("order_id", "country_name", "amount"))

print("""
WHY THIS MATTERS:
  SortMergeJoin:
    - Shuffles BOTH tables across the network (two Exchange nodes in the plan).
    - Sorts both sides.
    - Then merges them.

  BroadcastHashJoin:
    - Sends the SMALL table to every executor in memory (no shuffle for it).
    - Each executor does a local hash lookup for its partition of the big table.
    - Zero Exchange nodes for the small side = no network cost for it.

  The broadcast threshold (default 10 MB) is the file size below which Spark
  automatically chooses BroadcastHashJoin when reading from Parquet/Delta/files.
  For in-memory DataFrames (createDataFrame) Spark cannot estimate the size,
  so the threshold does not trigger -- always use F.broadcast() explicitly.
""")


# ═══════════════════════════════════════════════════════════════════════════════
# PROBLEM 3 – Data skew: one task does 90 % of the work
# ═══════════════════════════════════════════════════════════════════════════════
banner("PROBLEM 3 – Data skew")

spark.conf.set("spark.sql.shuffle.partitions", "8")

print("""
WHAT TO LOOK FOR IN SPARK UI:
  1. Run the BAD query below.
  2. Go to Stages tab -> click the aggregate stage.
  3. Scroll down to the Task table and sort by "Duration" descending.
  4. You will see something like:

       Task 0:  duration=0.01s   records=~10 000   (UK rows)
       Task 1:  duration=0.01s   records=~6 000    (DE rows)
       Task 2:  duration=0.01s   records=~4 000    (FR rows)
       Task 3:  duration=2.50s   records=~280 000  (US rows <- THE STRAGGLER)

  Tasks 0-2 finish instantly. Task 3 keeps running.
  The whole job cannot finish until Task 3 is done -- even if 7 cores are idle.
  This is data skew: data is not evenly distributed across tasks.
""")

bad_q3 = (
    orders
    .groupBy("country")
    .agg(
        F.count("*").alias("order_count"),
        F.sum("amount").alias("total_amount"),
        F.avg("amount").alias("avg_amount"),
    )
)
print("--- explain() for skewed groupBy ---")
bad_q3.explain()
run("BAD skewed groupBy (watch the Stages tab for the straggler task)", bad_q3)

print("""
--- FIX: salting -- spread the hot key across multiple tasks ---

Salting works in two steps:
  Step 1: add a random number (0..N-1) to the groupBy key
          "US" becomes "US_0", "US_1", "US_2", "US_3"
          Now 4 tasks share the US load instead of 1.
  Step 2: aggregate again dropping the salt
          merge the 4 partial US results back into one "US" row.
""")

SALT = 4  # split each key into 4 sub-groups

salted = orders.withColumn("salt", (F.rand(seed=99) * SALT).cast("int"))

step1 = (
    salted
    .groupBy("country", "salt")
    .agg(
        F.count("*").alias("order_count"),
        F.sum("amount").alias("total_amount"),
    )
)

good_q3 = (
    step1
    .groupBy("country")
    .agg(
        F.sum("order_count").alias("order_count"),
        F.sum("total_amount").alias("total_amount"),
        (F.sum("total_amount") / F.sum("order_count")).alias("avg_amount"),
    )
)
print("--- explain() for salted groupBy (two aggregation stages, more balanced tasks) ---")
good_q3.explain()
run("FIXED salted groupBy (task durations should be more balanced)", good_q3)

print("""
WHY SALTING WORKS:
  Without salt: all ~270 000 US rows go to the SAME task (same hash of "US").
  With salt=4:  rows split into US_0, US_1, US_2, US_3 groups.
                Each goes to a different task -> 4 parallel tasks for US.
  The second aggregation merges the 4 partial results into one "US" row.

  Trade-off: an extra shuffle stage. Worth it when skew causes one task to
  run 10x-100x longer than its peers.

  Spark 3+ AQE handles skew JOIN automatically when enabled:
    spark.conf.set("spark.sql.adaptive.enabled", "true")
  But for groupBy you still often need manual salting.
""")


# ── cleanup ──────────────────────────────────────────────────────────────────
banner("All 3 problems demonstrated. Spark UI still live at http://localhost:4040")
input("Press Enter to stop Spark and close the UI...\n")
spark.stop()
