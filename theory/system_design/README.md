# System Design

Worked case studies plus the reference material they draw on. Each case follows the same shape: **size it → draw it → justify each block → name the failure modes → summarise in two minutes.**

---

## Case studies

| Case | Core problem | Exercises |
| --- | --- | --- |
| [Truck stream processor](truck-stream-processor/README.md) | Detect when a truck goes silent and alert operators live | Streaming ingestion, event-time processing, hot/cold split, snapshot+stream dashboards |
| [Live load board](live-load-board/README.md) | Real-time freight marketplace board with live updates and no double-booking | **In-memory databases** (Redis structures, geo/sorted sets), booking races, pub/sub fan-out |
| [CDC: Postgres → warehouse](cdc-postgres-to-warehouse/README.md) | Get operational data to analysts within 5 minutes without touching the primary | **SQL ↔ NoSQL ↔ warehouse integration**, CDC, merge/upsert, schema evolution, backfills |
| [Document ingestion pipeline](document-ingestion-pipeline/README.md) | Extract structured fields from PDFs with LLMs, catch what's wrong | **AWS service composition**, Step Functions, Textract + Bedrock, human-in-the-loop |
| [Freight billing warehouse](freight-billing-warehouse/README.md) | Daily revenue & margin reporting finance can close the books on | **Python · SQL · dbt · Snowflake · Airflow** — ELT layering, incremental models, SCD2, data quality, warehouse cost |
| [Warehouse refactor & consolidation](warehouse-refactor-consolidation/README.md) | Inherit a 4-year-old production warehouse: untrusted numbers, duplicates, runaway cost | **Brownfield work** — dedup diagnosis, strangler consolidation, safe migration, cost attribution, DAG refactor |

## Reference

| Doc | Covers |
| --- | --- |
| [Streaming tools](99-reference/streaming-tools.md) | Transport vs processor. SQS/Kinesis/Kafka/Pulsar, Flink/Spark/Lambda/Kafka Streams, event time, watermarks, delivery semantics, streaming SQL |
| [In-memory databases](99-reference/in-memory-databases.md) | Redis/Valkey/Memcached/Dragonfly, Redis data structures as design tools, caching patterns, invalidation, stampede/penetration/avalanche, eviction |
| [SQL vs NoSQL](99-reference/sql-vs-nosql.md) | Database families and how to choose, polyglot persistence, dual-write anti-pattern, outbox, CDC, saga, consistency models |
| [AWS services map](99-reference/aws-services-map.md) | Services organised by the question they answer, plus five reference architectures worth memorising |
| [Cloud architecture comparison](../cloud/architecture-comparison.md) | The core toolkit on AWS, the 10 / 10k / 100k trucks scale ladder, and the AWS services in each case |
| [Snowflake performance & cost](../data-engineering/snowflake-performance.md) | Micro-partitions & pruning, reading a Query Profile, spilling, clustering (and when not to), warehouse sizing, caching layers, ACCOUNT_USAGE cost attribution |

---

## The method

**1 — Size it before naming anything.** Compute events/s, bytes/day and the size of the hot working set. These numbers decide the design. "333 events/s" turns a Kafka cluster into one Kinesis shard; "the hot set is 25 MB" justifies putting it in RAM. Volunteering the arithmetic unprompted is the strongest signal in the whole interview.

**2 — Draw the boxes, then defend each one.** Every component should answer "what breaks if I delete this?" If there's no answer, delete it.

**3 — Separate the hot path from the cold path.** Almost every data system splits into *what's happening now* (low latency, small, key-based → Redis/DynamoDB) and *what happened* (high volume, analytical → S3/Snowflake). Same writer, two sinks. Recognising which question a component serves resolves most design arguments.

**4 — One store owns the truth; everything else is a derived view.** If a derived store is lost, you rebuild it from the log. This single principle answers most "how do you keep these in sync" questions — and it's why the dual-write anti-pattern is worth naming out loud.

**5 — Name the failure modes unprompted.** Duplicates, late and out-of-order events, backpressure, poison messages, thundering herds, alert storms. Interviewers are largely testing whether you've operated a system, and this is where that shows.

**6 — State the trade-off you're accepting.** Not "I'd use Flink" but "I'd use Flink because it gives per-key event-time timers; the cost is that the state now lives in the job and a bad deploy can replay alerts." Every choice has a price — say it before you're asked.

**7 — Size the answer to the question.** Propose the *boring* design that fits the stated scale, then describe the growth path. Reaching for Kafka and Flink on a 10k-device problem reads as inexperience, not sophistication.

---

## Recurring patterns across these cases

| Pattern | Appears in |
| --- | --- |
| **Snapshot + stream** (pull full state on load, subscribe for deltas) | Truck processor console, live load board |
| **Hot store + cold store** from one writer | The five build-it cases |
| **Derived views rebuilt from a log** | Load board (Redis), CDC (warehouse), doc pipeline (OpenSearch) |
| **Idempotency via conditional write** | Truck processor, CDC merge, document dedupe |
| **The database arbitrates, the cache optimises** | Load board booking race |
| **At-least-once delivery + idempotent consumer = effectively-once** | All six |
| **Strangler: build beside, prove equivalence, migrate readers, then delete** | Warehouse refactor |
| **Measure before you change; prove impact against a baseline** | Warehouse refactor |
| **Bounded retries → DLQ → alarm** | All six |
| **Raw zone is append-only, so a bad transform is a re-run not a re-extract** | CDC, freight billing warehouse, doc pipeline |
| **Lookback window for late-arriving data** | Freight billing warehouse, CDC |
