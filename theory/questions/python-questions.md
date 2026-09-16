# Python — Questions & Typing Drills

Two halves: concepts you get **asked**, and syntax you have to **type from memory** under observation. The second half matters more if your daily coding is AI-assisted. Recognising code and producing it cold are different skills, and a live exercise tests only the second. Theory: [../backend/python-general.md](../backend/python-general.md) and [../backend/python_graphs.py](../backend/python_graphs.py).

---

## Language

<details><summary><b>Q1.</b> List vs tuple vs set vs dict: when does each win?</summary>

**A.** Pick by the operation you do most: a set or dict when you look things up, a list when you keep order and append.
- **list:** ordered, mutable, `O(n)` membership.
- **tuple:** immutable and hashable (if its items are), so it can be a dict key.
- **set:** `O(1)` average membership and dedup, unordered.
- **dict:** `O(1)` average key lookup, insertion-ordered since 3.7.

The one that actually comes up: `if x in my_list` inside a loop is `O(n·m)`. Convert to a set first; it's the most common easy win in a live exercise.
</details>

<details><summary><b>Q2.</b> Generator vs list comprehension.</summary>

**A.** A list comprehension builds everything in memory now; a generator yields one item at a time, on demand. `[x for x in it]` vs `(x for x in it)`.

For a 10 GB file the list version runs out of memory and the generator streams. Generators also chain without materialising intermediates. Trade-off: you can iterate only once, and you can't index or take `len()`.
</details>

<details><summary><b>Q3.</b> What's the mutable default argument trap?</summary>

**A.** Default values are evaluated **once, at definition time**, so a mutable default is shared across every call and accumulates.
```python
def add(item, target=[]):   # WRONG: one list shared by all calls
    target.append(item)
    return target
```
Fix with a `None` sentinel:
```python
def add(item, target=None):
    if target is None:
        target = []
    target.append(item)
    return target
```
Don't "fix" it with `target = target or []`. A caller who passes their own **empty** list gets a new list instead, so the mutation they expected never reaches their object. `is None` is the only correct check.
</details>

<details><summary><b>Q4.</b> Explain the GIL and what it means practically.</summary>

**A.** In standard CPython only one thread runs Python bytecode at a time, so threads don't give you CPU parallelism.

In practice:
- **Threads for I/O-bound work** (API calls, DB queries), because the GIL is released while waiting.
- **Processes for CPU-bound work** (`multiprocessing`, `ProcessPoolExecutor`), or push the compute to a database or Spark.

Current state: Python 3.13 shipped an experimental free-threaded build, and 3.14 made it **officially supported but still opt-in** (`python3.14t`). Assume the GIL unless told otherwise; many C extensions aren't free-threading-ready yet.
</details>

<details><summary><b>Q5.</b> `async`/`await`: when is it worth it?</summary>

**A.** When you have many concurrent I/O waits, like hundreds of API calls or open sockets. It's cooperative concurrency on one thread, so it avoids the per-thread overhead.

It's not worth it for CPU work, which blocks the loop, or for a script making three sequential calls. The catch: one blocking call inside a coroutine (`requests.get`, `time.sleep`) stalls the whole event loop, so the call stack has to be async-aware (`httpx`, `asyncio.sleep`).
</details>

<details><summary><b>Q6.</b> `__init__` vs `__new__`, and what's a dataclass for?</summary>

**A.** `__new__` creates the instance and `__init__` initialises it. You almost never touch `__new__` outside singletons or subclasses of immutable types.

`@dataclass` generates `__init__`, `__repr__` and `__eq__` from type annotations. For the data-holding classes that make up most pipeline code, it removes the boilerplate where bugs hide. Use `frozen=True` for value objects.
</details>

<details><summary><b>Q7.</b> What does a context manager do and how do you write one?</summary>

**A.** A context manager guarantees cleanup even when an exception is raised.

```python
import time
from contextlib import contextmanager

@contextmanager
def timer(label):
    start = time.perf_counter()
    try:
        yield
    finally:
        print(f"{label}: {time.perf_counter() - start:.2f}s")
```
Everything before `yield` is setup and everything in `finally` is teardown. Use it for connections, file handles, temp directories and locks.
</details>

<details><summary><b>Q8.</b> Shallow vs deep copy.</summary>

**A.** A shallow copy duplicates the outer container but shares the objects inside it; a deep copy recurses. `copy.copy` is shallow and `copy.deepcopy` is deep, so mutating a nested item in a shallow copy mutates the original's item too.

It bites most often with a list of dicts: copy the list, edit a dict inside it, and both change.
</details>

---

## Data engineering in Python

<details><summary><b>Q9.</b> Process a 50 GB CSV on a machine with 8 GB of RAM.</summary>

**A.** Never load it whole. Usually the right answer is to not process it in Python at all. In order of preference:

1. **Push it to the warehouse:** `COPY INTO` from S3 and transform in SQL. Say this first.
2. **Out-of-core engines:** DuckDB or Polars (streaming) scan larger-than-memory files directly and are much faster than pandas.
3. **Stream it:** iterate line by line and aggregate incrementally.
4. **Chunked reads:** `pd.read_csv(..., chunksize=100_000)`, reducing each chunk.
</details>

<details><summary><b>Q10.</b> Write an idempotent extractor. What makes it idempotent?</summary>

**A.** Re-running it for the same window must produce the same result, with no gaps and no double-counting.
```python
def extract(source, data_interval_start, data_interval_end):
    rows = source.fetch(since=data_interval_start - timedelta(minutes=15),  # overlap
                        until=data_interval_end)
    for i, batch in enumerate(chunked(rows, 5_000)):
        key = f"{prefix}/{data_interval_start:%Y%m%dT%H%M}/part-{i:05}.json"
        s3.put_object(Bucket=B, Key=key, Body=serialize(batch))
```
- It's keyed on the **run window**, not `now()`.
- It re-reads a small **overlap**, so late-committing rows and clock skew don't create gaps.
- It writes to a **deterministic key per window**, so a retry overwrites the same objects instead of adding new ones. Clear the window prefix first if the batch count can shrink.

The overlap means consecutive windows share rows, so the **load** must dedup too: `MERGE` on primary key + `updated_at`.
</details>

<details><summary><b>Q11.</b> How do you retry an API call properly?</summary>

**A.** Exponential backoff **with jitter**, bounded attempts, and retry only what's retryable. 429 and 5xx are worth retrying; 400 and 401 never are, because they'll fail the same way forever.

```python
for attempt in range(5):
    r = session.get(url, timeout=30)
    if r.status_code < 400:
        return r.json()
    if r.status_code == 429 or r.status_code >= 500:
        time.sleep(min(2 ** attempt + random.random(), 60))
        continue
    r.raise_for_status()
raise RuntimeError(f"gave up after 5 attempts: {url}")
```
Without jitter, every client retries in lockstep and you rebuild the thundering herd you were avoiding. Honour `Retry-After` when present. Only retry a `POST` if it carries an **idempotency key**; otherwise a retry can double-create.
</details>

<details><summary><b>Q12.</b> Paginate an API you don't control.</summary>

**A.** Prefer **cursor-based** pagination when it's offered. Offset pagination silently skips or repeats rows when the data changes mid-scan.

```python
def fetch_all(url, params):
    cursor = None
    while True:
        page = get(url, params={**params, "cursor": cursor}).json()
        yield from page["data"]
        cursor = page.get("next_cursor")
        if not cursor:
            break
```
Yield rather than accumulate, so memory stays flat and the caller can stream to disk.
</details>

<details><summary><b>Q13.</b> How do you test data pipeline code?</summary>

**A.** Separate the **logic** from the **I/O**, so the logic is a pure function you can test with small fixtures. Then:
- **Unit tests** on transforms, with handcrafted inputs that include the nasty cases: nulls, duplicates, timezone edges.
- **Integration tests** against a real warehouse clone in CI.
- **Data tests** (dbt) on the output.

If your transform can only be tested by running the whole DAG, it's structured wrong.
</details>

---

## Typing drills

Type these **from memory**, with no autocomplete, then compare. Fluency here is what a live exercise measures.

<details><summary><b>D1.</b> Group a list of dicts by a key.</summary>

```python
from collections import defaultdict

grouped = defaultdict(list)
for row in rows:
    grouped[row["customer_id"]].append(row)

# or, for sorted input:
from itertools import groupby
rows.sort(key=lambda r: r["customer_id"])
for key, group in groupby(rows, key=lambda r: r["customer_id"]):
    ...
```
`itertools.groupby` groups only **consecutive** items, so forgetting to sort first is the classic bug.
</details>

<details><summary><b>D2.</b> Count occurrences and get the top 3.</summary>

```python
from collections import Counter
counts = Counter(r["carrier"] for r in rows)
counts.most_common(3)
```
</details>

<details><summary><b>D3.</b> Deduplicate preserving order.</summary>

```python
seen, out = set(), []
for x in items:
    if x not in seen:
        seen.add(x)
        out.append(x)

# or, since dicts keep insertion order:
out = list(dict.fromkeys(items))
```
</details>

<details><summary><b>D4.</b> Chunk an iterable into batches of n.</summary>

```python
from itertools import islice

def chunked(iterable, n):
    it = iter(iterable)
    while batch := list(islice(it, n)):
        yield batch
```
It works on a generator without materialising it, which matters when the source is a 50 GB file. On 3.12+, `itertools.batched(iterable, n)` does this and yields tuples.
</details>

<details><summary><b>D5.</b> Merge two dicts, right wins.</summary>

```python
merged = {**a, **b}      # any version
merged = a | b           # 3.9+
```
</details>

<details><summary><b>D6.</b> Sort by multiple keys, one descending.</summary>

```python
rows.sort(key=lambda r: (r["carrier"], -r["amount"]))
# non-numeric descending needs two passes (sort is stable):
rows.sort(key=lambda r: r["date"], reverse=True)
rows.sort(key=lambda r: r["carrier"])
```
</details>

<details><summary><b>D7.</b> Read a large file line by line and parse JSON.</summary>

```python
import json, logging

def read_jsonl(path):
    bad = 0
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                bad += 1            # never let one poison line kill the run
                logging.warning("bad json at line %d", lineno)
```
</details>

<details><summary><b>D8.</b> A retry decorator.</summary>

```python
import functools, time, random

def retry(times=3, base=1.0):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(times):
                try:
                    return fn(*args, **kwargs)
                except Exception:
                    if attempt == times - 1:
                        raise
                    time.sleep(base * 2 ** attempt + random.random())
        return wrapper
    return deco
```
`functools.wraps` preserves the function name and docstring; interviewers notice when it's missing.
</details>

<details><summary><b>D9.</b> Parallel I/O with a thread pool.</summary>

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=10) as ex:
    futures = {ex.submit(fetch, url): url for url in urls}
    for fut in as_completed(futures):
        url = futures[fut]
        try:
            results.append(fut.result())
        except Exception as e:
            log.warning("failed %s: %s", url, e)
```
Threads, because the work is I/O-bound. Handle exceptions per future: `fut.result()` re-raises, and one failure shouldn't lose the other nine.
</details>

<details><summary><b>D10.</b> Type hints for a pipeline function.</summary>

```python
from collections.abc import Iterator, Sequence
from datetime import datetime

def extract(
    source: str,
    since: datetime,
    columns: Sequence[str] | None = None,
) -> Iterator[dict[str, object]]:
    ...
```
Modern style: builtin generics (`dict[str, int]`), `X | None` over `Optional[X]`, and `collections.abc` over `typing.List`.
</details>

<details><summary><b>D11.</b> Shortest path on a grid with BFS.</summary>

```python
from collections import deque

def shortest_path(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    queue = deque([(start, 0)])
    seen = {start}
    while queue:
        (r, c), dist = queue.popleft()
        if (r, c) == goal:
            return dist
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols \
               and grid[nr][nc] != "#" and (nr, nc) not in seen:
                seen.add((nr, nc))
                queue.append(((nr, nc), dist + 1))
    return -1
```
BFS gives the shortest path on unweighted graphs. Mark `seen` **when enqueuing**, not when popping, or the same cell enters the queue many times. `deque.popleft()` is `O(1)`; `list.pop(0)` is `O(n)`.
</details>

<details><summary><b>D12.</b> Topological sort with cycle detection (Kahn's algorithm).</summary>

```python
from collections import defaultdict, deque

def topo_sort(edges):                 # edges: [(upstream, downstream), ...]
    graph, indegree = defaultdict(list), defaultdict(int)
    nodes = set()
    for a, b in edges:
        graph[a].append(b)
        indegree[b] += 1
        nodes |= {a, b}
    queue = deque(n for n in nodes if indegree[n] == 0)
    order = []
    while queue:
        n = queue.popleft()
        order.append(n)
        for m in graph[n]:
            indegree[m] -= 1
            if indegree[m] == 0:
                queue.append(m)
    if len(order) != len(nodes):
        raise ValueError("cycle detected")
    return order
```
This is exactly how Airflow and dbt order a DAG. If some nodes never reach indegree 0, there's a cycle, which is why the length check matters.
</details>
