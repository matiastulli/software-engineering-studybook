# System Design — Questions

Grounded in the six cases in [../system_design/README.md](../system_design/README.md). Answer out loud before opening.

---

## The method

<details><summary><b>Q1.</b> Walk me through how you approach a system design question you've never seen.</summary>

**A.** Clarify, size, draw, name the failure modes, then state the trade-off. Sizing is the step candidates skip, and it decides everything else.

1. **Clarify the requirement:** who uses it, how fresh the data must be, what breaks if it's wrong.
2. **Size it** out loud: events/second, bytes/day, size of the hot working set.
3. **Draw the boxes**, then justify each one by asking "what breaks if I delete this?"
4. **Name the failure modes** unprompted: duplicates, late data, backpressure, poison messages.
5. **State the trade-off you're accepting** and the growth path if the numbers change.
</details>

<details><summary><b>Q2.</b> Why does sizing matter so much before naming technologies?</summary>

**A.** Because it turns an opinion into a decision. 10,000 trucks at one event per 30 seconds is 333 events/s. One Kinesis shard takes 1,000 records/s, so the answer is a single shard and a Lambda, not a Kafka cluster. And 10k × ~2.5 KB of hot state is 25 MB, which fits in RAM and justifies Redis without hand-waving.

Reaching for Kafka and Flink on a 10k-device problem reads as inexperience, not sophistication. The numbers protect you from that.
</details>

<details><summary><b>Q3.</b> What's the single principle that resolves most "how do we keep these in sync" questions?</summary>

**A.** **One store owns the truth; everything else is a derived view rebuilt from a log.**

You don't synchronise peers; you replay into replicas. If Redis dies, rebuild it from Postgres. If the warehouse is wrong, re-run the transform over the raw zone. The principle also shows at once why dual writes are an anti-pattern: they create two peers with no ordering and no atomicity.
</details>

<details><summary><b>Q4.</b> What is the hot path / cold path split and why does almost every data system have one?</summary>

**A.** Because systems answer two different questions:

- **"What's happening now":** low latency, small data, key-based access → DynamoDB, Redis.
- **"What happened":** high volume, analytical scans → S3, Snowflake.

The same writer feeds two sinks. Naming which question a component serves resolves most design arguments, because people argue about the tool when they actually disagree about the access pattern.
</details>

<details><summary><b>Q5.</b> An interviewer proposes a design you think is wrong. What do you do?</summary>

**A.** Say so, with a reason and a number, then keep building. *"Routing through the database to detect silence adds a round-trip to the alerting path. At 10k trucks that's fine; past a few hundred thousand I'd move detection into the stream. Want me to design it the simple way and note the growth path?"*

Having an opinion is what's being tested. Silent agreement reads as no experience; refusing to build reads as inflexible.
</details>

---

## Streaming & real-time

<details><summary><b>Q6.</b> Design a system that alerts when an IoT device stops reporting.</summary>

**A.** At 10k trucks the boring polling design is correct. Size first: 10k trucks × 1 event/30 s = **333 events/s**, and the hot state is one row per truck, 10k rows.

Kinesis with `truck_id` as the partition key → Lambda consumer writing `last_seen` to DynamoDB and raw events to S3 (via Firehose) → an EventBridge-scheduled job checks for silence every minute → SNS → console.

**Switch when** the fleet passes a few hundred thousand devices or the SLO drops below a minute. Then move detection into the stream with **per-key event-time timers** (Flink, or Spark 4 `transformWithState`). Each event resets that truck's timer, and a timer that fires *is* the silence signal: no scan, no DB round-trip.
</details>

<details><summary><b>Q7.</b> Why is detecting the *absence* of an event harder than detecting an event?</summary>

**A.** Because nothing arrives to trigger the computation. Presence is reactive; absence needs either a scheduled scan over state or a timer per key that fires when nothing resets it.

That's why per-key timers are the feature to name. Flink has had them for years, and Spark added them in `transformWithState`. Stateless Lambda and plain SQL can't do it without an external scheduler and a scan.
</details>

<details><summary><b>Q8.</b> A truck reconnects after 3 hours and replays buffered events. What breaks?</summary>

**A.** Everything that assumed arrival order. That's why the system must use **event time**, the timestamp from the device, not the clock when you received it.

Watermarks let a window close despite this: a watermark of T asserts "no more events older than T". Too tight and you drop late data; too loose and alerts lag. Also decide what happens to events behind the watermark: drop them, send them to a side output, or correct them in batch. And make sure old replayed pings can't move `last_seen` backwards; use a conditional write on event time.
</details>

<details><summary><b>Q9.</b> Who feeds a live operator console? The stream processor?</summary>

**A.** No. The processor writes state, and a separate API serves it over three paths:

1. **Snapshot (pull):** on page load, a query API over the hot store returns the full current state. Only this can answer "show all 10,000 trucks sorted by silence duration".
2. **Deltas (push):** a WebSocket fed from the alert topic sends only changes.
3. **History (pull, slow):** a separate endpoint over Snowflake.

Why the processor must not serve HTTP:
- You couldn't scale reads independently.
- Deploys and checkpoint restores would drop connections.
- Auth belongs in an API layer.
- The console's query shape (sort by duration, filter by region, paginate) is a database query, not a stream operation.
</details>

---

## Data engineering

<details><summary><b>Q10.</b> ETL or ELT, and why?</summary>

**A.** **ELT** with a modern warehouse: land raw data untransformed, then transform inside the warehouse with dbt.

Transforming before loading throws away the ability to reprocess without re-extracting, and Snowflake does the transform better than your Python box. The exception is data you're legally required to mask or drop before it lands (PII, card data). That redaction happens in the E, not the T.
</details>

<details><summary><b>Q11.</b> Why keep a raw zone if it's redundant with the curated tables?</summary>

**A.** Because it turns every transform bug from a re-extraction into a re-run. The raw zone is append-only and complete. When you find a parser bug three months later, you replay from it instead of asking a vendor to resend files they no longer have.

It also makes backfills cheap. And analysts shouldn't query it: revoke `SELECT` from the analyst role, so a schema change there can't break a dashboard.
</details>

<details><summary><b>Q12.</b> Carrier invoices arrive 2–10 days after delivery. How does your incremental model handle that?</summary>

**A.** Filter on **when the row landed**, re-read a trailing window, and merge on the unique key. A naive `where invoice_date > (select max(invoice_date) from {{this}})` silently skips every invoice dated before the current max. Margin ends up understated permanently, and no test catches it.

```sql
{% if is_incremental() %}
  where _loaded_at >= (select dateadd(day, -3, max(_loaded_at)) from {{ this }})
{% endif %}
```
The merge makes reprocessing idempotent; the lookback covers loader retries and clock skew. If only a business date exists, the lookback must cover the full lateness (10+ days). Add a periodic rebuild of the trailing 30 days, or use dbt `microbatch` with a lookback.
</details>

<details><summary><b>Q13.</b> Why is a database write becoming an event a hard problem, and what's the fix?</summary>

**A.** The naive version is a **dual write**: write the row, then publish the event. There's no atomicity, so a crash between the two causes permanent, silent drift.

Two correct fixes:
- **Transactional outbox:** write the business row and an `outbox` row in one local transaction; a relay publishes from the outbox. The local transaction provides the atomicity, and you control the event shape.
- **CDC:** read the database's own replication log. Non-invasive, and it catches *everything*, including migrations and manual `UPDATE`s the outbox misses. The cost: your table schema becomes the contract, and a stalled replication slot can fill the source's disk.

Both give at-least-once delivery, so consumers must be idempotent.
</details>

---

## Brownfield & production

<details><summary><b>Q14.</b> You inherit a warehouse nobody trusts. What do you do first?</summary>

**A.** Measure for two weeks before changing anything. `ACCOUNT_USAGE` gives spend by warehouse, the top queries by credits, tables unread in 90 days, and duplicate rates per fact.

That baseline is how you earn permission for the slow work and how you prove impact later. Then sequence the work:
1. **Cost:** reversible config changes, visible within a week, which buy credibility.
2. **Reliability.**
3. **Dedup.**
4. **Consolidation.**

Attempting consolidation in week two, before anyone trusts you, is how these projects die.
</details>

<details><summary><b>Q15.</b> How do you refactor something people depend on?</summary>

**A.** **Strangler pattern**, never big-bang. Build the replacement beside the original, shadow-run it and diff nightly against real traffic, migrate consumers one at a time, then delete.

The general rule is **additive first, subtractive last, with a monitored gap between.** The gap is where you discover who depended on the thing you were about to drop. For tables, the old names become views over the new model, so consumers change nothing.
</details>

<details><summary><b>Q16.</b> Your corrected model shows revenue 4% lower than the table finance has been using. Now what?</summary>

**A.** That's a business conversation, not a technical one. Explain every discrepancy **in writing** before migrating, get finance to sign off, and land the change on a period boundary.

Even an unexplained 0.3% difference will surface in an audit six months later with your name on it. Shipping a silent restatement is the real failure mode here.
</details>

<details><summary><b>Q17.</b> How do you dedup an 800M-row table without downtime?</summary>

**A.** Never `DELETE` in place. Build the fixed table beside it and swap:

1. Build the corrected table beside it with `QUALIFY ROW_NUMBER()`.
2. Reconcile: row counts, sums of every measure, per-month diff.
3. Clone the original as a rollback point (zero-copy).
4. `ALTER TABLE ... SWAP WITH ...`, an atomic metadata operation that's effectively instant.
5. Keep the clone for a deprecation window, then drop it.

Readers never see a half-migrated state, and rollback is a second swap. Pause the writers during steps 1–4, or replay what landed in between.
</details>

<details><summary><b>Q23.</b> A live load board has 5,000 carriers watching and ~50 changes/s. How do you keep screens in sync?</summary>

**A.** **Snapshot + filtered deltas**, never broadcast-everything. Broadcasting every change to every screen is 50 × 5,000 = **250k messages/s**, almost all irrelevant.

1. On open, the client does an HTTP GET for a snapshot of its filtered view (from Redis), including a `version`/`as_of`.
2. It opens a WebSocket subscribed to a **coarse channel derived from its filters** (`board:dallas:reefer`).
3. A projector publishes each change only to matching channels; the client discards deltas older than its snapshot.

Failure modes to name:
- **Reconnect storm** after a deploy: jittered client backoff, and a fresh snapshot on reconnect, never a blind resume.
- **Hot channel** (Chicago reefer): split into sub-buckets.
- **Projector lag:** booked loads linger and carriers hit 409s. Alarm on projection lag.
</details>

---

## Tool choice

<details><summary><b>Q18.</b> "Why not Spark?"</summary>

**A.** Volume. At ~2 GB/day incremental, a Snowflake `MERGE` handles it, and a three-person team shouldn't operate a cluster. I'd revisit past roughly a TB/day, or for work that isn't SQL-shaped, like ML feature engineering or heavy custom parsing.

The general form of this answer: name the number, name the team size, and name the threshold where you'd change your mind.
</details>

<details><summary><b>Q19.</b> "Why dbt instead of stored procedures?"</summary>

**A.** Version control, lineage, testing, documentation and CI. Stored procedures give you none of that by default, and they're hard to review as a diff.

dbt also has no compute of its own: it compiles SQL and sends it to the warehouse. So you're not adding a processing tier, just discipline around the one you have.
</details>

<details><summary><b>Q20.</b> When would you choose Step Functions over chained Lambdas?</summary>

**A.** When the unit of work is a stateful, multi-minute, failure-prone workflow, like a document going through OCR, extraction and validation.

Step Functions gives:
- Per-step retries with backoff.
- A visible execution graph.
- Wait states for async jobs, and `Map` for fan-out.
- Standard workflows that run far past Lambda's 15-minute limit.

Chained Lambdas through SQS get the same throughput with none of the observability. When a customer asks where document 4471 is, you want to point at an execution graph.
</details>

<details><summary><b>Q21.</b> Airflow or Step Functions?</summary>

**A.** Airflow for scheduled data pipelines with dependencies, backfills and sensors that the data team owns. Step Functions for per-request or per-event workflows that need retries and durable state, defined in IaC next to the services.

Many shops run both, and that's not a failure: they solve different problems.
</details>

<details><summary><b>Q22.</b> When would you use Snowflake Streams + Tasks or Dynamic Tables instead of Airflow?</summary>

**A.** When the whole pipeline lives inside Snowflake and freshness matters, because both remove an entire orchestration system.

- **Dynamic Tables:** declarative, with a `SELECT` and a target lag.
- **Streams + Tasks:** imperative, for custom `MERGE` logic.

Don't use them when the pipeline spans SFTP, S3 and three APIs. Airflow's backfill ergonomics and cross-system visibility are worth more than the latency saved. Naming the option and then explaining why you're not taking it is stronger than not knowing it exists.
</details>
