# Databases & Caching — Questions

Theory: [../system_design/99-reference/sql-vs-nosql.md](../system_design/99-reference/sql-vs-nosql.md), [../system_design/99-reference/in-memory-databases.md](../system_design/99-reference/in-memory-databases.md), [../system_design/cdc-postgres-to-warehouse/README.md](../system_design/cdc-postgres-to-warehouse/README.md), [../backend/rest-apis-webhooks.md](../backend/rest-apis-webhooks.md).

---

## Choosing a store

<details><summary><b>Q1.</b> SQL or NoSQL: how do you actually decide?</summary>

**A.** Default to Postgres, and reach past it only when you can name the specific reason. It does JSONB, PostGIS, pgvector, full-text search and LISTEN/NOTIFY, and operating one database beats operating four.

Ask three questions in order:
1. Do I need multi-row **ACID transactions**? → relational.
2. Is the access pattern **fully known and key-based** at extreme scale? → key-value (DynamoDB).
3. Do I need **ad-hoc analytics** over lots of rows? → columnar warehouse.

Everything else → relational.
</details>

<details><summary><b>Q2.</b> What's DynamoDB's real constraint?</summary>

**A.** You model the table around the queries, so an access pattern you didn't foresee later means a new GSI or a migration.

That's fine when patterns are stable and known: session store, per-device state, idempotency keys. It's painful when the product is still changing shape, and "we'll figure out the queries later" is exactly when it hurts. Pick DynamoDB when you can write the access patterns down on day one; pick Postgres when you can't.
</details>

<details><summary><b>Q3.</b> Why is a warehouse columnar and an operational database row-oriented?</summary>

**A.** Row storage keeps a whole record together, so reading or updating one row touches one place, which suits transactions. Columnar storage keeps each column together, so scanning one column across a billion rows reads only that column and compresses very well, which suits aggregation.

That's why a single-row lookup feels slow in Snowflake and a `SUM` over 800M rows feels slow in Postgres: each is being asked to do the other's job.
</details>

<details><summary><b>Q4.</b> When does OpenSearch earn its place?</summary>

**A.** For full-text search, fuzzy matching and **arbitrary filter combinations**, like "silent trucks in Texas carrying refrigerated loads", where DynamoDB would need a GSI per pattern.

It should never be the source of truth. It's a derived index you can rebuild (Q18), and treating it as authoritative is how people lose data.
</details>

---

## Redis & in-memory

<details><summary><b>Q5.</b> What makes Redis more than a cache?</summary>

**A.** Its data structures. Sorted sets, hashes, sets, bitmaps, HyperLogLog and geo indexes make it a design tool, not just a key-value blob store.

"Which trucks haven't pinged since T" is `ZRANGEBYSCORE` on a sorted set scored by last-seen timestamp. That's an `O(log N + M)` range query instead of a table scan, already sorted by how long each truck has been quiet.
</details>

<details><summary><b>Q6.</b> Name a Redis structure and the problem it solves.</summary>

**A.** Each structure maps to a classic problem:
- **Sorted set** → leaderboards, silence detection, sliding-window rate limits.
- **`SET key val NX PX 5000`** → short lock or idempotency guard.
- **Hash** → update one field of an object without rewriting the blob.
- **HyperLogLog** → unique counts over billions of items in ~12 KB at ~0.81% error.
- **Bitmap** → daily-active flags: 1M users in ~125 KB.
- **Geo** → "trucks within 50 km".
</details>

<details><summary><b>Q7.</b> Redis or Valkey?</summary>

**A.** **Valkey** is the usual default on AWS now. When Redis moved to source-available licences in 2024, AWS, Google, Oracle and others backed Valkey, a BSD-licensed fork under the Linux Foundation. It's drop-in compatible, and ElastiCache prices it lower than Redis OSS (approx. 20% on node-based clusters, checked 2026-09).

For accuracy: **Redis 8 (2025) added AGPLv3** as a licence option, so Redis is open source again. Many companies still avoid AGPL, though. Knowing both halves of that story is a cheap credibility signal.
</details>

<details><summary><b>Q8.</b> Cache-aside vs write-through vs write-behind.</summary>

**A.** Cache-aside is the default: simple, and it survives losing the cache.
- **Cache-aside:** the app checks the cache; on a miss it reads the DB and populates the cache.
- **Write-through:** writes go to cache and DB synchronously. Always fresh, but every write pays both latencies.
- **Write-behind:** write to the cache and flush to the DB asynchronously. Fastest, but it **can lose data**, so only for tolerable-loss data like view counters.

With cache-aside, invalidate (delete the key) on write rather than setting the new value. Two concurrent writers can otherwise leave the older value in the cache.
</details>

<details><summary><b>Q9.</b> Name the three cache failure modes.</summary>

**A.** Stampede, penetration and avalanche.

- **Stampede:** a hot key expires and thousands of requests miss at once, all hitting the DB. At 5,000 req/s on a key whose query takes 200 ms, about 1,000 identical queries start before the first refill lands. Fix with a short lock (`SET NX`) so one request refills while the others wait or serve stale, or with probabilistic early refresh.
- **Penetration:** repeated lookups for keys that don't exist pass straight through to the DB. Cache the negative result briefly, or use a Bloom filter.
- **Avalanche:** many keys with identical TTLs expire together, or the cache node restarts cold. Jitter the TTLs and warm critical keys.
</details>

<details><summary><b>Q10.</b> Which eviction policy, and what's the trap?</summary>

**A.** `allkeys-lru` (or `allkeys-lfu`) for a pure cache. **`noeviction` when Redis holds state you can't regenerate**, so it fails loudly rather than silently dropping your data.

The trap is running a state store, like the live load board index, on an evicting policy. It quietly evicts under memory pressure, and loads vanish with no error anywhere. Pair `noeviction` with a memory alarm.
</details>

<details><summary><b>Q11.</b> When should you *not* add a cache?</summary>

**A.** When it adds an invalidation bug without a measured gain.
- **Low hit rate:** a cache with a low hit rate (as a rough rule, under ~80%) adds a network hop and complexity for little gain.
- **Strong consistency required:** the data must be correct on every read.
- **Already fast:** the underlying query is already fast enough.

Measure first. "Add a cache" is the most common unnecessary answer in system design, so the stronger move is an index or a read replica.
</details>

---

## Consistency & integration

<details><summary><b>Q12.</b> Why are dual writes an anti-pattern?</summary>

**A.** Writing to two systems without a shared transaction has no atomicity and no ordering. A crash between the two writes leaves permanent drift, and the drift is silent: you find out months later from a customer.

Fix it with the **transactional outbox** (write the row and an event row in one local transaction, then a relay publishes) or with **CDC**.
</details>

<details><summary><b>Q13.</b> Outbox or CDC?</summary>

**A.** Outbox when you own the app and want a stable event contract; CDC when you don't control the writers or need every change.

- **Outbox:** a clean, intentional contract, since you decide what gets published and in what shape. It misses writes that bypass the application, like migrations and manual `UPDATE`s.
- **CDC:** non-invasive and captures everything, but it turns your internal schema into the event contract, so a column rename becomes a breaking change downstream. It also adds replication-slot operations (Q19).
</details>

<details><summary><b>Q14.</b> Explain eventual consistency to a stakeholder.</summary>

**A.** *"The change is saved, and every copy will agree within a second or two. A dashboard might briefly show the old number."*

Then be precise about where that's not acceptable: payments and bookings need strong consistency, a truck-location dashboard doesn't. The skill is choosing the right model for each piece of data rather than one globally.
</details>

<details><summary><b>Q15.</b> What's read-your-writes and why do users complain about it?</summary>

**A.** A user should always see *their own* change, even when replicas lag. Without it, someone saves a form, the read hits a lagging replica, and the UI shows the old value: the classic "it didn't save" bug report.

Implementations:
- Pin that user's reads to the primary for a few seconds after a write.
- Or return the write's position (Postgres LSN, a version number) and read from a replica only once it has caught up to it.
</details>

<details><summary><b>Q16.</b> CAP theorem: answer without reciting it.</summary>

**A.** Network partitions happen; you don't get to opt out. What you choose is what happens *during* one: refuse writes to stay consistent, or accept them and reconcile later.

Apply it per data type: payments choose consistency, a location dashboard chooses availability. PACELC adds the everyday half: even without a partition, you trade latency for consistency (for example, synchronous vs async replication). Reciting "pick two of three" without applying it is the weak answer.
</details>

<details><summary><b>Q17.</b> What's a saga?</summary>

**A.** A way to run a business transaction across services that can't share a database transaction: a sequence of local transactions, each with a **compensating action** (charge → refund, reserve → release).

Pick **orchestration** (Step Functions, Temporal) over choreography (a chain of events) once there are more than two or three steps. A failure is then visible in one place instead of being reconstructed from five services' logs. Compensations must be idempotent, because they get retried too.
</details>

<details><summary><b>Q18.</b> How do you keep a search index in sync with the database?</summary>

**A.** Don't write to both. Emit changes from the database, through CDC or an outbox, and have a consumer project them into the index.

The index becomes a derived view: if it's wrong or lost, you replay the log or re-index from the source. Same principle as every multi-store question: one store owns the truth.
</details>

<details><summary><b>Q19.</b> Your Debezium consumer was down all weekend. Why might the production Postgres be in trouble?</summary>

**A.** Because an **inactive logical replication slot makes Postgres retain WAL** until the consumer confirms it. If the consumer is down long enough, the primary's disk fills and the database stops accepting writes. Your analytics pipeline has just taken down production.

- **Detect:** alarm on retained WAL per slot, e.g. `pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn)`, and on free disk.
- **Prevent:** set `max_slot_wal_keep_size` (Postgres 13+). The slot gets invalidated instead of filling the disk, and you re-snapshot.
- **Runbook:** "drop the slot and re-snapshot" must be documented, so on-call can save the primary at 3am.

Trade-off: a WAL cap protects production but can force a full re-snapshot. For a small team, DMS or a managed connector shifts some of this work away, but the slot risk remains.
</details>

<details><summary><b>Q20.</b> Two retries with the same Idempotency-Key arrive 20 ms apart. What goes wrong with a simple cache, and how do you fix it?</summary>

**A.** Both requests check the cache, both miss (the first hasn't finished), and **both run the handler**, so the card is charged twice. A "look up, then store the response" cache is itself a check-then-act race.

Fix: **claim the key atomically before doing the work.**
1. `INSERT INTO idempotency_keys (key, request_hash, status='in_progress')`, relying on a **unique constraint**, or `SET key NX PX 60000` in Redis. Exactly one request wins.
2. The loser gets `409 Conflict` (or waits) while the key is in progress, and replays the stored response once it completes.
3. If the same key arrives with a different `request_hash`, return `422`/`409`: the client reused a key by mistake.
4. The winner stores the final status and body, with a TTL (e.g. 24 h).

Store keys in Postgres when the side effect is in the same DB; the claim and the business write can then share one transaction. An in-memory `Map` breaks with more than one instance or on restart.
</details>

<details><summary><b>Q21.</b> Two carriers click "Book" on the same load within 40 ms. Redis lock or database?</summary>

**A.** **The database decides; Redis only reduces contention.** The correctness mechanism is a conditional update on the source of truth:

```sql
UPDATE loads SET status = 'booked', carrier_id = :carrier
 WHERE id = :load_id AND status = 'open';
-- 1 row → you won; 0 rows → return 409 LOAD_ALREADY_BOOKED
```

It's atomic, needs no distributed lock, and the row count *is* the answer. A Redis `SET NX` lock in front can still reject most doomed second clicks cheaply. But if Redis is down or a lock expires during a GC pause, bookings must still be correct. Never use a Redis lock as the only guard on a money-moving operation.
</details>
