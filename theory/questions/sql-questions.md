# SQL — Questions

Advanced SQL is a JD bullet and the thing most likely to appear as a live exercise. Write the query out before opening the answer. The theory lives in [../data-engineering/sql-advanced.md](../data-engineering/sql-advanced.md).

---

## Window functions

<details><summary><b>Q1.</b> Explain window functions to someone who only knows GROUP BY.</summary>

**A.** `GROUP BY` collapses rows; a window function keeps every row and adds a column computed over a related set of rows.

```sql
select order_id, customer_id, amount,
       sum(amount) over (partition by customer_id) as customer_total,
       amount / sum(amount) over (partition by customer_id) as pct_of_customer
from orders
```
You get one row per order, plus each customer's total. With `GROUP BY` alone you'd need to join back to an aggregate to get both.
</details>

<details><summary><b>Q2.</b> ROW_NUMBER vs RANK vs DENSE_RANK.</summary>

**A.** They differ only in how they handle ties. On values 10, 10, 9:
- `ROW_NUMBER` → 1, 2, 3 (always unique; ties broken arbitrarily)
- `RANK` → 1, 1, 3 (ties share, then it skips)
- `DENSE_RANK` → 1, 1, 2 (ties share, no gap)

Use `ROW_NUMBER` for dedup and top-N-per-group, `RANK` when ties genuinely tie and you want the gap, and `DENSE_RANK` for levels without gaps.
</details>

<details><summary><b>Q3.</b> Deduplicate to the latest row per key.</summary>

**A.** Number the rows per key, newest first, and keep row 1. In Snowflake:
```sql
select * from raw.shipments
qualify row_number() over (
    partition by shipment_id
    order by updated_at desc, _loaded_at desc, _file_row_number desc
) = 1
```
The portable version wraps it in a subquery with `where rn = 1`.

**The ordering must be total.** `order by updated_at desc` alone is non-deterministic when timestamps tie, so the query can return different rows on different runs. Add columns until the order is unique.
</details>

<details><summary><b>Q4.</b> Compute a running total and a month-over-month change.</summary>

**A.** A running `sum` with an explicit frame, and `lag` for the previous month:
```sql
select month, revenue,
       sum(revenue) over (order by month
                          rows between unbounded preceding and current row) as running_total,
       revenue - lag(revenue) over (order by month)                          as mom_change,
       div0(revenue - lag(revenue) over (order by month),
            lag(revenue) over (order by month))                              as mom_pct
from monthly_revenue
```
Be explicit with the frame. With `ORDER BY`, the default is `range between unbounded preceding and current row`, and `RANGE` includes all peer rows on ties, a subtle source of wrong running totals.
</details>

<details><summary><b>Q5.</b> Find each customer's top 3 orders by amount.</summary>

**A.** `ROW_NUMBER` partitioned by customer, ordered by amount, filtered to `<= 3`. Top-N-per-group is the most common window-function interview question.
```sql
select * from (
  select o.*, row_number() over (partition by customer_id order by amount desc) as rn
  from orders o
) where rn <= 3
```
If ties should all be included ("top 3 amounts"), use `DENSE_RANK` instead and say why.
</details>

<details><summary><b>Q6.</b> Find gaps: days with no shipments in the last 90 days.</summary>

**A.** You can't find missing rows by querying the table that's missing them. Generate a date spine and anti-join:
```sql
with days as (
  select dateadd(day, row_number() over (order by seq4()) - 1,
                 dateadd(day, -90, current_date)) as d
  from table(generator(rowcount => 91))
)
select d.d
from days d
where not exists (select 1 from shipments s where s.delivered_date = d.d)
```
Use `row_number()` rather than raw `seq4()`: Snowflake documents that `SEQ4` can produce gaps, and a gap in your spine hides a gap in your data.
</details>

<details><summary><b>Q7.</b> Sessionize events: group into sessions with a 30-minute inactivity gap.</summary>

**A.** Use the gaps-and-islands pattern: flag each row that starts a new session, then a running `sum` of the flags becomes the session id.
```sql
with flagged as (
  select *, case when datediff(minute,
                    lag(event_at) over (partition by user_id order by event_at),
                    event_at) > 30 then 1 else 0 end as is_new_session
  from events
)
select *, sum(is_new_session) over (partition by user_id order by event_at
                                    rows unbounded preceding) as session_id
from flagged
```
The same pattern solves a surprising number of problems, such as truck trips split by stops or price periods.
</details>

---

## Joins & grain

<details><summary><b>Q8.</b> Your totals doubled after adding a join. What happened?</summary>

**A.** A **fan-out**: the joined table isn't unique on the join key, so each left row matched several right rows.

Diagnose by counting rows before and after the join. Fix the grain: aggregate the right side to one row per key before joining, or correct the join condition.

**Don't add `distinct`.** It hides a modelling bug, and it's wrong the moment two legitimate rows are identical.
</details>

<details><summary><b>Q9.</b> How do you verify a join is 1:1 before writing it?</summary>

**A.** Compare the row count to the distinct key count on the side that should be unique:
```sql
select count(*), count(distinct join_key) from right_table;
```
Equal means unique (watch for NULL keys, which `count(distinct)` ignores). dbt makes this permanent as a `unique` test on the key, so it can't silently regress.
</details>

<details><summary><b>Q10.</b> Why is `LEFT JOIN` with a filter in WHERE a trap?</summary>

**A.** A condition on the right table in `WHERE` silently turns the left join into an inner join. The filter runs after the join, and the NULLs from unmatched rows fail the predicate.

```sql
-- accidentally an inner join:
left join invoices i on i.shipment_id = s.id
where i.status = 'paid'

-- what you meant:
left join invoices i on i.shipment_id = s.id and i.status = 'paid'
```
</details>

<details><summary><b>Q11.</b> When is a self-join the right tool?</summary>

**A.** Rarely, now that window functions exist. Comparing a row to the previous row is `LAG`, not a self-join on `id - 1`.

The legitimate uses are hierarchies (employee → manager in the same table) and pairwise comparisons like "all pairs of shipments on the same lane within an hour". Otherwise a self-join usually means a window function was the answer.
</details>

---

## Performance

<details><summary><b>Q12.</b> A query is slow. What's your general approach?</summary>

**A.** Read the plan before changing anything, then look for wasted reads before structural fixes. In order:
1. Is it reading far more rows than it returns (a pruning or index failure)?
2. Is it spilling to disk?
3. Is a join exploding row counts?
4. Is it doing work it doesn't need: `select *` on a wide columnar table, an unnecessary `ORDER BY`, a `distinct` compensating for a bad join?

Only after that consider structural changes like clustering or an index.
</details>

<details><summary><b>Q13.</b> Why does `where date(created_at) = '2025-03-01'` hurt?</summary>

**A.** A function on the column stops the engine from using what it knows about the raw column. It defeats a plain B-tree index in Postgres and can defeat partition pruning in Snowflake. Use a range:
```sql
where created_at >= '2025-03-01' and created_at < '2025-03-02'
```
Same result, and it can use the index or prune. In Postgres, the alternative is an expression index on `date(created_at)`.
</details>

<details><summary><b>Q14.</b> CTE vs subquery vs temp table: does it matter?</summary>

**A.** Mostly it's readability, so prefer CTEs. The exceptions are old Postgres and expensive results reused many times.

- **Postgres before v12:** every CTE was materialised separately (an optimisation fence), which is where the old "avoid CTEs" advice comes from.
- **Postgres 12+:** a CTE is inlined if it's non-recursive, has no side effects and is **referenced once**. Referenced twice or more, it's materialised unless you write `NOT MATERIALIZED`.
- **Snowflake:** the optimiser decides, and a CTE referenced several times may be computed once.

A temp table earns its place when an expensive intermediate result is reused across several statements.
</details>

<details><summary><b>Q15.</b> `EXISTS` vs `IN` vs `JOIN` for filtering.</summary>

**A.** Default to `EXISTS` / `NOT EXISTS` for pure filtering, because it's NULL-safe and never duplicates rows.

`NOT IN` with a NULL anywhere in the subquery returns **no rows at all**, a nasty silent bug. `JOIN` duplicates rows if the right side isn't unique. Modern optimisers often plan `IN` and `EXISTS` the same way, so the choice is about correctness, not speed.
</details>

<details><summary><b>Q16.</b> What's the N+1 query problem?</summary>

**A.** Fetching a list, then issuing one query per row: 1 + N round trips. It's common in ORMs and in Python loops that call the database for each item.

Fix it with one query and a join, or by batching keys with `WHERE id IN (...)`; in an ORM, use eager loading. The tell is a log full of identical queries that differ only by id.
</details>

---

## Correctness

<details><summary><b>Q17.</b> How does NULL break aggregations?</summary>

**A.** Aggregates skip NULLs and arithmetic propagates them, so numbers go quietly wrong.

- `COUNT(col)` skips NULLs; `COUNT(*)` doesn't.
- `SUM` and `AVG` ignore NULLs, so `AVG` over a column that's 50% NULL averages only the non-null half.
- Arithmetic with NULL yields NULL, so `revenue - cost` is NULL when cost is missing and silently drops out of a later `SUM`.

Use `coalesce` deliberately, and decide whether missing means zero or unknown. They're different.
</details>

<details><summary><b>Q18.</b> Why store amount, currency and FX rate separately?</summary>

**A.** A pre-converted figure can't be audited or reproduced. Rates are point-in-time, so converting with today's rate silently restates last March.

Store the original amount, its currency and the rate actually used, then derive the converted value. It's the same principle as an SCD2 rate card.
</details>

<details><summary><b>Q19.</b> Timezones: what's the rule?</summary>

**A.** Store UTC everywhere and convert once, at the presentation boundary. Keep the timezone explicit in the column type (`timestamp_tz` / `timestamptz`).

"Revenue on the 31st" differs depending on the timezone used to bucket it, and finance will find the discrepancy. Agree the reporting timezone once and apply it in one place.
</details>

<details><summary><b>Q20.</b> Write a query to find duplicates and tell me what kind they are.</summary>

**A.** Count rows per key, and count distinct row contents alongside:
```sql
select shipment_id, count(*) as n,
       count(distinct hash(* exclude (_loaded_at, _file_name))) as distinct_versions
from fct_shipments
group by 1 having count(*) > 1
order by n desc
```
Exclude load metadata columns, or every row looks distinct.
- `distinct_versions = 1` → identical rows: a pipeline re-run problem.
- `> 1` → different versions of the same entity: version history is being read as current state. That's a modelling problem, fixed with a `QUALIFY` in staging.

Same symptom, completely different fix. Diagnosing which one you have *is* the skill.
</details>

<details><summary><b>Q21.</b> Why is this query bad? `select a.* from a join b on a.id = b.id or a.hash = b.hash`</summary>

**A.** An `OR` in a join predicate isn't a simple equi-join. The engine usually can't use a hash or merge join, degrades toward a nested loop (O(n×m)), and can return duplicates when a row matches on both conditions.

The intent is usually "match on id, fall back to hash". Say that, then fix it:
- **Two left joins + `COALESCE`** for the fallback intent.
- **`UNION`** of two equi-joins when either match counts.

Both give the optimiser two clean equi-joins. At 1M × 1M rows, that's the difference between seconds and never finishing. Always check whether the fallback join can fan out too.
</details>

<details><summary><b>Q22.</b> Your Postgres extract uses `where updated_at > :last_watermark`. What can go wrong?</summary>

**A.** It silently misses rows at the boundary, and it never sees deletes. A missing index on `updated_at` only makes it slow; it doesn't lose rows.

- **Late-committing transactions:** a transaction sets `updated_at = now()` at 10:00:00 but commits at 10:00:05. Your extract ran at 10:00:02 and moved the watermark to 10:00:02, so that row is behind the watermark forever.
- **Boundary ties:** `>` with a watermark equal to some rows' timestamp skips the rows that share it.
- **Deletes:** a deleted row has no `updated_at` to find.
- **Unreliable column:** app code or manual `UPDATE`s that don't bump `updated_at`.

Fixes: re-read an overlap (watermark minus a few minutes) and make the load an idempotent `MERGE`. Maintain `updated_at` with a trigger, and use soft deletes. When deletes or completeness matter, switch to log-based CDC. Run the extract against a read replica either way.
</details>

<details><summary><b>Q23.</b> Which isolation level should a full export from Postgres use, and why?</summary>

**A.** `REPEATABLE READ`. In Postgres it gives a **consistent snapshot**, so every query in the transaction sees the database as of its first statement: no non-repeatable reads and no phantoms, without blocking writers.

`READ COMMITTED` (the default) takes a new snapshot per statement. Exporting `orders` and then `order_lines` could see different points in time and produce orphan lines.

Two gotchas:
- A long snapshot holds back vacuum on the primary, so tables bloat. Run it on a **replica**, and expect long queries there to be cancelled by replication conflicts unless `hot_standby_feedback` is on, which pushes the bloat back onto the primary.
- MySQL/InnoDB's `REPEATABLE READ` also snapshots plain reads, but locking reads behave differently. Don't assume the textbook table ("repeatable read allows phantoms") describes your engine.
</details>
