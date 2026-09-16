# Streaming & Messaging — Questions

Theory: [../system_design/99-reference/streaming-tools.md](../system_design/99-reference/streaming-tools.md). Scale anchor: 10k trucks × 1 ping / 30 s = **333 events/s**.

---

## Choosing

<details><summary><b>Q1.</b> SQS vs SNS vs EventBridge: one line each.</summary>

**A.** SQS is a work queue, SNS is broadcast, EventBridge is content-based routing.
- **SQS:** consumers pull work from a queue; each message is processed by one consumer.
- **SNS:** push one message to many subscribers, with optional filter policies.
- **EventBridge:** route by message *content* across services and SaaS, with a schema registry and archive/replay.

Default: EventBridge for integration events between services, SQS for work queues. SNS → SQS fan-out when several services each need their own copy with independent retry.
</details>

<details><summary><b>Q2.</b> Queue vs log: what's the actual difference?</summary>

**A.** A queue deletes a message once it's processed; a log keeps an ordered history that each consumer reads at its own offset.

- **Queue** (SQS): destructive. A consumer takes a message, acks it, and it's gone.
- **Log** (Kafka, Kinesis): retained. Many consumers read the same data independently, and you can replay from any point.

The deciding question: *do I need to re-read this later, or have several independent consumers?* If yes, you need a log. Bridge: a log offset is a checkpoint you own, like the watermark in an incremental dbt model.
</details>

<details><summary><b>Q3.</b> Kinesis or Kafka?</summary>

**A.** **Kinesis** if you're on AWS and don't want to run brokers. It's managed, integrates natively (Lambda, Firehose), and the shard maths is simple. **Kafka/MSK** when you need its ecosystem (Connect, Debezium, Streams), compacted topics, cross-cloud portability, or high sustained throughput where per-shard pricing gets expensive.

Retention is no longer the differentiator: Kinesis retains up to 365 days (extra cost). Sizing matters more than preference: at 333 events/s Kinesis needs one shard, and a 12-broker Kafka cluster is an absurd answer.
</details>

<details><summary><b>Q4.</b> How do you size Kinesis shards?</summary>

**A.** Each shard ingests **1 MB/s or 1,000 records/s**, whichever you hit first, and serves 2 MB/s of reads (shared across standard consumers). So `shards = ceil(max(MB_per_sec / 1, records_per_sec / 1000))`, plus headroom.

For the trucks: 333 records/s at ~1 KB each ≈ 330 KB/s → **one shard**. At 100k trucks, 3,333 records/s → 4 shards, say 6 with headroom. Say the arithmetic out loud. If traffic is spiky or unknown, **on-demand mode** removes the shard maths at a higher unit price.
</details>

<details><summary><b>Q5.</b> Lambda, Flink, or Spark Structured Streaming?</summary>

**A.** Lambda for stateless per-message work, Flink for serious stateful event-time logic, Spark when the team already lives in Spark.

- **Lambda:** cheapest, scales to zero, no real windowing or keyed state.
- **Flink** (Managed Service for Apache Flink): windows, keyed state and **per-key event-time timers**; the most mature engine for detecting an *absence* of events.
- **Spark Structured Streaming:** micro-batch with a latency floor of seconds. Spark 4's `transformWithState` adds timers, so it can do absence detection too.

Reusing the team's existing skills legitimately beats a marginally better engine.
</details>

---

## Semantics

<details><summary><b>Q6.</b> At-most-once, at-least-once, exactly-once: which do you actually build?</summary>

**A.** At-least-once delivery plus idempotent consumers, which gives "effectively-once". That's the sentence interviewers are listening for.

- **At-most-once:** loses data on failure.
- **At-least-once:** the realistic default; duplicates happen.
- **Exactly-once:** real *inside a closed system* (Flink checkpoints with a transactional sink, Kafka transactions), but not across arbitrary external side effects like an email or an HTTP call.
</details>

<details><summary><b>Q7.</b> How do you actually make a consumer idempotent?</summary>

**A.** Make processing the same message twice a no-op, by giving it a key and making the write conditional on it.

- **Conditional put:** `PutItem` with `ConditionExpression: event_time > last_event_time`.
- **Dedup table:** store `event_id` with a TTL and skip if present, written atomically (conditional insert) rather than check-then-write.
- **Upsert on a unique key:** `MERGE`, not `INSERT`.
- **Deterministic object key:** a re-delivery overwrites itself.
</details>

<details><summary><b>Q8.</b> Event time vs processing time.</summary>

**A.** Event time is when it happened at the source; processing time is when your job saw it. Anything involving mobile devices, retries or replay must use **event time**. Otherwise a truck that reconnects after three hours dumps its events into the wrong windows.

Processing time is only acceptable when ordering doesn't matter, as in a raw archive or throughput metrics.
</details>

<details><summary><b>Q9.</b> Explain watermarks like I've never heard of them.</summary>

**A.** A watermark at time T is the stream saying: *"I don't expect any more events older than T."* That's what lets a window close and emit a result; otherwise you'd wait forever for stragglers.

A typical watermark is "max event time seen minus 5 minutes". Set it too tight and you drop late data; too loose and every result lags. It's an explicit completeness-vs-latency trade-off, and saying so is the point of the question.
</details>

<details><summary><b>Q10.</b> Tumbling, sliding, session windows.</summary>

**A.** Fixed buckets, overlapping buckets, and gap-based buckets.
- **Tumbling:** fixed and non-overlapping, like hourly counts.
- **Sliding (hopping):** overlapping, like a 5-minute average updated every minute.
- **Session:** grouped until a gap of inactivity (say 30 minutes). The natural fit for trip or user-session detection; it's the streaming version of the SQL gaps-and-islands pattern.
</details>

---

## Operations

<details><summary><b>Q11.</b> What's backpressure and how do you detect it?</summary>

**A.** The consumer is slower than the producer, so the backlog grows. In Kinesis watch `GetRecords.IteratorAgeMilliseconds` (or Lambda's `IteratorAge`); in Kafka, consumer group lag.

**Alarm on it.** It's the earliest warning that a pipeline is degrading, and it usually climbs for hours before anything breaks. Mitigate by adding parallelism (more shards or partitions, or a Lambda parallelisation factor), batching writes to the sink, or shedding non-critical work.
</details>

<details><summary><b>Q12.</b> One malformed message keeps failing and blocking the shard. Fix?</summary>

**A.** Bounded retries, then route it to a **dead-letter queue**, and alarm on DLQ depth. Never retry unboundedly on the main path: a poison message halts everything behind it, and in an ordered log that means the whole partition stops.

For a Lambda on Kinesis, that's `MaximumRetryAttempts`, `BisectBatchOnFunctionError` and an on-failure destination. The DLQ needs an owner and a replay runbook, or it silently fills for months.
</details>

<details><summary><b>Q13.</b> What's a hot partition and how do you avoid it?</summary>

**A.** A skewed partition key sends most traffic to one shard, which throttles while the others sit idle. Keying by `region` puts 60% of the load on one shard; keying by `truck_id` spreads evenly.

**Detect it:** per-shard `WriteProvisionedThroughputExceeded` on Kinesis, or one partition's lag far above the rest in Kafka. It's the streaming version of Spark skew: one task far slower than the others.

**Fix:** a higher-cardinality key, or a composite key (`region#bucket`) re-aggregated downstream. Partition key choice *is* your throughput ceiling, and it also decides your ordering (Q14).
</details>

<details><summary><b>Q14.</b> Ordering: what does Kinesis actually guarantee?</summary>

**A.** Order **per shard**, not globally. Same partition key → same shard → ordered; different keys can interleave arbitrarily. Resharding can briefly break this unless consumers finish the parent shard first, which the KCL does.

So design around per-entity ordering: partition by the entity whose sequence matters. If you think you need global ordering across the stream, you probably have a single-writer problem in disguise.
</details>

<details><summary><b>Q15.</b> Kafka consumer groups, briefly.</summary>

**A.** Within a group, each partition is assigned to exactly one consumer, so parallelism is capped at the partition count. An eleventh consumer on a 10-partition topic sits idle. Bridge: partitions are to consumers what Spark partitions are to tasks.

Separate groups each get the full stream independently, which is how several applications fan out. Kafka 4.x adds **share groups** (queue-like consumption with per-message acks, GA in 4.2), which remove the partition cap for work-queue use cases.
</details>

<details><summary><b>Q16.</b> When would you use Redis Streams over Kafka?</summary>

**A.** When volume is modest and Redis is already in the stack. You get consumer groups, acks and replay without operating another system.

Not when you need long retention, high throughput, or durability stronger than Redis's persistence model. Naming it shows you're sizing the problem rather than reaching for the biggest tool.
</details>

<details><summary><b>Q17.</b> When do you commit the offset: before or after the side effect?</summary>

**A.** **After** the side effect succeeds. That's at-least-once, so the side effect must be idempotent.

- **Commit before, crash after:** the message is marked done but never processed → **data loss** (at-most-once).
- **Commit after, crash before committing:** the message is reprocessed on restart → **duplicate**, which an idempotent write absorbs.

Kafka's auto-commit commits on a timer regardless of whether processing finished, so it can do either. Turn it off for anything that matters. Also expect duplicates on every **rebalance**: a partition moves to a new consumer, which resumes from the last committed offset.
</details>

<details><summary><b>Q18.</b> An event arrives after the watermark has passed. What happens, and what should happen?</summary>

**A.** By default the window has already closed, so the event is dropped. You should decide explicitly, per metric, whether late data matters.

- **Allowed lateness:** keep window state a little longer and emit an updated result. The sink must accept upserts, not appends.
- **Side output:** route late events to a separate stream or table and reconcile them.
- **Batch correction:** the raw events land in S3 anyway, so a nightly job recomputes yesterday from event time. The streaming result is "fast and approximate", the batch result is the record.

Always count late events. A rising late-event count is how you notice a fleet of devices with bad clocks or buffering problems.
</details>
