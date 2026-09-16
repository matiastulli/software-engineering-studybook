# Python for live coding: patterns you can type from memory

## TL;DR

- Live coding tests **fluency**, not cleverness. The logic is usually a GROUP BY, a dedup or a sort; what fails is fumbling `sorted(key=...)`, `heapq` or `defaultdict` under pressure.
- Six templates cover most data-engineer exercises: **group-by with a dict, dedup keeping the latest, flatten nested JSON, stream a file in chunks, merge intervals, retry with backoff**.
- Pick structures by the operation you repeat: membership → `set`; pop from the front → `deque`; "smallest/largest next" → `heapq`; lookup by key → `dict`.
- I/O-bound → threads (or `asyncio` for thousands of connections); CPU-bound → processes.
- Say the plan out loud, handle empty input first, then type the template.

Drills: [python-questions.md](../questions/python-questions.md) (the `D`-numbered typing drills) and the timed exercises in [`practical/typing_drills/`](../../practical/typing_drills/). Graphs and recursion: [python_graphs.py](python_graphs.py).

---

## 1. The problem

You're handed 50,000 GPS pings from 10 trucks as a list of dicts and 30 minutes: "latest ping per truck, total km per carrier, flag overlapping loads." In SQL you'd write it in three minutes (`QUALIFY ROW_NUMBER()`, `GROUP BY`, a self-join). In Python, with autocomplete off, people lose ten minutes remembering whether it's `heapq.heappush(h, x)` or `h.heappush(x)`. The fix is not more theory; it's a small set of templates typed until they're automatic.

**Bridges from what you already know**

| Python | Is the same idea as |
|---|---|
| `defaultdict(list)` / `defaultdict(int)` group-by | `GROUP BY` with `ARRAY_AGG` / `SUM` |
| dict keyed by id, keep max `updated_at` | `QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC) = 1` |
| generator (`yield`, `(x for x in ...)`) | a lazy Spark transformation: nothing runs until something consumes it |
| `heapq.nlargest(k, rows, key=...)` | `ORDER BY ... LIMIT k` without sorting everything |
| `sorted(rows, key=lambda r: (r["a"], -r["b"]))` | `ORDER BY a, b DESC` |

---

## 2. Data-engineering staples (most asked first)

### 2.1 Group-by with a dict

```python
from collections import defaultdict

km_by_carrier = defaultdict(float)
loads_by_carrier = defaultdict(list)
for r in rows:
    km_by_carrier[r["carrier"]] += r["km"]
    loads_by_carrier[r["carrier"]].append(r["load_id"])

# plain-dict version when defaultdict isn't allowed
totals = {}
for r in rows:
    totals[r["carrier"]] = totals.get(r["carrier"], 0) + r["km"]
```

`itertools.groupby` only groups **consecutive** keys: sort by the same key first, or use the dict.

### 2.2 Dedup keeping the latest record

```python
latest = {}
for r in rows:
    k = r["load_id"]
    if k not in latest or r["updated_at"] > latest[k]["updated_at"]:
        latest[k] = r
result = list(latest.values())
```

O(n), one pass, no sort. ISO-8601 strings compare correctly as strings; `"01/20/2026"` does not, so parse mixed formats first. Order-preserving dedup of plain values: `list(dict.fromkeys(items))`.

### 2.3 Flatten nested JSON

```python
def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}{k}."))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}{i}."))
    else:
        out[prefix[:-1]] = obj          # strip trailing "."
    return out

flatten({"truck": {"id": 7, "gps": [40.1, -3.7]}})
# {'truck.id': 7, 'truck.gps.0': 40.1, 'truck.gps.1': -3.7}
```

Say the edge cases: empty dicts/lists disappear, and a list of 1,000 stops becomes 1,000 columns. For arrays you often want to **explode into rows** instead (the Snowflake `LATERAL FLATTEN` / Spark `explode` choice).

### 2.4 Read a big file in chunks with generators

```python
import json
from itertools import islice

def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        for line in f:                  # the file object is already lazy
            if line.strip():
                yield json.loads(line)

def batches(iterable, n):
    it = iter(iterable)
    while batch := list(islice(it, n)):
        yield batch

for batch in batches(read_jsonl("pings.jsonl"), 10_000):
    load_to_warehouse(batch)            # memory = one batch, not the 50 GB file
```

CSV: `csv.DictReader(f)` is also lazy. Python 3.12+ has `itertools.batched(iterable, n)`, which yields tuples.

### 2.5 Merge overlapping intervals

```python
def merge_intervals(intervals):
    merged = []
    for start, end in sorted(intervals):            # sort by start
        if merged and start <= merged[-1][1]:       # overlaps the last one
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged

merge_intervals([(1, 3), (8, 10), (2, 6)])  # [[1, 6], [8, 10]]
```

O(n log n) for the sort. Use `max` because a later interval can sit entirely inside the previous one. Use `<` instead of `<=` if touching intervals (`[1,3]`, `[3,5]`) shouldn't merge.

### 2.6 Retry with exponential backoff

```python
import random, time

def retry(fn, attempts=5, base=0.5, cap=30, retry_on=(ConnectionError, TimeoutError)):
    for attempt in range(attempts):
        try:
            return fn()
        except retry_on:
            if attempt == attempts - 1:
                raise                                   # give up loudly
            delay = min(cap, base * 2 ** attempt)
            time.sleep(random.uniform(0, delay))        # jitter avoids a thundering herd
```

Only retry **transient** errors (timeouts, 429, 5xx), never a 400. Retries are safe only if the call is idempotent; see [rest-apis-webhooks.md](rest-apis-webhooks.md) for idempotency keys.

### 2.7 Top-k, two pointers, sliding window

```python
import heapq
heapq.nlargest(3, rows, key=lambda r: r["km"])   # O(n log k)

def max_window_sum(arr, k):                      # fixed window
    s = best = sum(arr[:k])
    for i in range(k, len(arr)):
        s += arr[i] - arr[i - k]
        best = max(best, s)
    return best

def longest_unique_substring(s):                 # variable window
    last, left, best = {}, 0, 0
    for right, ch in enumerate(s):
        if last.get(ch, -1) >= left:
            left = last[ch] + 1
        last[ch] = right
        best = max(best, right - left + 1)
    return best
```

Recursion and DP in one template: add `@functools.cache` to the recursive function (top-down), or fill a table bottom-up when depth could pass the default recursion limit of 1000. Graphs: [python_graphs.py](python_graphs.py).

---

## 3. Signatures that get fumbled

```python
sorted(rows, key=lambda r: (r["carrier"], -r["km"]), reverse=False)  # returns a NEW list
rows.sort(key=...)                      # in place, returns None; both are stable

d.get(k, default)                       # no KeyError
d.setdefault(k, []).append(x)           # group-by without defaultdict
for k, v in d.items(): ...              # .items() — not iterating d, which gives keys
max(d, key=d.get)                       # key with the largest value

from collections import Counter, deque, defaultdict
Counter(words).most_common(3)           # [('a', 5), ...]
q = deque(); q.append(x); q.popleft()   # BFS queue

import heapq                            # module functions on a plain list, MIN-heap
heapq.heappush(h, (priority, item))
heapq.heappop(h)
heapq.heapify(nums)                     # O(n), in place, returns None
heapq.heappush(h, (-score, item))       # max-heap: negate

import bisect
bisect.bisect_left(sorted_list, x)      # insertion index

for i, x in enumerate(items, start=1): ...
for a, b in zip(xs, ys, strict=True): ...   # 3.10+: error on length mismatch

", ".join(str(x) for x in items)        # join is a method of the separator
line.strip().split(",")

json.loads(text); json.dumps(obj, default=str)   # default=str handles datetimes
from datetime import datetime
datetime.fromisoformat("2026-01-15T10:00:00")
datetime.strptime("01/20/2026", "%m/%d/%Y")
```

---

## 4. Decide

**Which structure**

| You repeatedly need to... | Use | Why not the obvious alternative |
|---|---|---|
| check "have I seen this?" | `set` | `x in list` is O(n); in a loop that's O(n²) |
| look up by key / group | `dict` / `defaultdict` | |
| append and pop at the **end** (stack, DFS) | `list` | |
| pop from the **front** (queue, BFS, window) | `deque` | `list.pop(0)` is O(n) per pop |
| get the smallest/largest next, or top-k | `heapq` | re-sorting each time is O(n log n) per step |
| keep a sorted list while inserting | `bisect.insort` (small n) | `insort` is O(n) per insert because of the shift |

**Threads vs processes vs asyncio**

- **Threads** (`ThreadPoolExecutor`) when the work is I/O-bound: 200 API calls, S3 downloads, DB queries. The GIL is released while waiting on I/O.
- **Processes** (`ProcessPoolExecutor`) when it's CPU-bound pure Python: parsing, hashing, number crunching. Each process has its own interpreter and GIL. Arguments get pickled, so don't ship huge objects.
- **asyncio** when you have thousands of concurrent connections and async client libraries (`aiohttp`, `asyncpg`). One blocking call (`requests.get`, `time.sleep`) stalls every task.
- **None of them** when the data is big: that's Spark/Snowflake. Real data-pipeline Python is mostly I/O.
- The default CPython build still has a GIL. Free-threaded builds exist from 3.13 but aren't the default (approx., checked 2026-09).

```python
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=10) as pool:
    results = list(pool.map(fetch_load, load_ids))   # keeps input order
```

---

## 5. Language questions that come up

- **Dynamically but strongly typed.** Types are checked at runtime, not compile time (dynamic), and there's no silent coercion: `"total: " + 42` raises `TypeError`, where JavaScript would coerce (strong). Duck typing means Python cares what an object can *do*, not what it *is*.
- **Type hints aren't enforced at runtime.** `mypy`/`pyright` check them. Use `list[int]`, `dict[str, float]`, `X | None` (3.10+).
- **`@dataclass`** for records (`field(default_factory=list)` for mutable defaults); an **ABC** with `@abstractmethod` for an interface like `Storage.read/write`; a **context manager** (`with`, or `__enter__`/`__exit__`) for anything that must be closed.
- **Dicts keep insertion order** (guaranteed since 3.7).

---

## 6. Common mistakes in live coding

1. **Mutable default argument.** `def f(data=[])` shares one list across calls. Use:
   ```python
   def f(data=None):
       if data is None:
           data = []
   ```
   Not `data = data or []`, which silently replaces an explicitly passed empty list (or `0`, `""`) with a new object, so the caller's list never gets mutated.
2. **Mutating a collection while iterating it.** Iterate a copy (`for x in list(items)`) or build a new one.
3. **`rows = rows.sort()`** sets `rows` to `None`. Same for `heapify` and `append`.
4. **Shadowing built-ins**: `list = [...]`, `dict = {}`, `id = ...`, `max = 0` break the built-in later in the function.
5. **`is` vs `==`**: `is` means same object. Use it only for `None`.
6. **`groupby` without sorting** gives repeated groups.
7. **`[[0] * m] * n`** creates n references to one row. Use `[[0] * m for _ in range(n)]`.
8. **Off-by-one**: `range(n)` is `0..n-1`, `5 // 2 == 2`, `-5 // 2 == -3`.
9. **Forgetting empty input and `return`.** Check `if not rows:` first; a function without `return` gives `None`.

## 7. Common wrong answers

- *"Generators make it faster."* They make it **lean on memory**; total work is the same. Like a lazy Spark plan, they only defer work.
- *"Use threads to speed up this CPU-heavy parse."* With the GIL, CPU-bound threads don't run in parallel. Use processes, or push the work into Spark/SQL.
- *"A list is fine as a queue."* `pop(0)` shifts every element. BFS over 100k nodes becomes quadratic.
- *"Retry on every exception."* Retrying a 400 or a bug just delays the failure, and retrying a non-idempotent POST creates duplicates.

---

## 8. Type these from memory (5 minutes each, autocomplete off)

1. Group rows by carrier: sum of km plus a list of load ids.
2. Dedup keeping the latest `updated_at` per `load_id`.
3. `flatten()` for nested dicts and lists.
4. `read_jsonl` + `batches` generator pipeline.
5. `merge_intervals`.
6. `retry` with exponential backoff and jitter.
7. Top-3 by a key with `heapq.nlargest`, then the same with `sorted(...)[:3]`.
8. BFS shortest path with `deque` (re-type from [python_graphs.py](python_graphs.py)).

---

## Self-check

<details><summary><b>Q1.</b> Why is <code>def f(data=None): data = data or []</code> wrong, and what do you write instead?</summary>

`or` tests truthiness, not `None`. If the caller passes their own empty list to be filled, `[] or []` picks a new list, so the caller's list is never mutated. The same happens with `0` or `""` in other types. Write `if data is None: data = []`.

</details>

<details><summary><b>Q2.</b> You get 2M load updates with duplicates. Keep the latest per load_id without sorting. What's the complexity, and what's the SQL equivalent?</summary>

One pass with a dict `load_id → record`, replacing when `updated_at` is newer: O(n) time and O(unique ids) memory. SQL: `QUALIFY ROW_NUMBER() OVER (PARTITION BY load_id ORDER BY updated_at DESC) = 1`. Watch for timestamps in mixed string formats, which don't compare correctly.

</details>

<details><summary><b>Q3.</b> BFS uses <code>deque</code>, top-k uses <code>heapq</code>. What breaks if you use a plain list for each?</summary>

A list as a BFS queue needs `pop(0)`, which is O(n), so BFS becomes O(n²). A list for top-k means sorting everything (O(n log n)) or rescanning for the max on every step, versus O(n log k) with a heap of size k.

</details>

<details><summary><b>Q4.</b> You need to call a carrier API for 5,000 loads, and each call takes ~200 ms. Threads, processes or asyncio?</summary>

This is I/O-bound. Sequentially it's 5,000 × 0.2 s ≈ 17 min. A `ThreadPoolExecutor` with 20 workers brings it to ≈ 50 s, limited by the API's rate limit rather than by Python. asyncio also works with an async HTTP client. Processes add pickling and startup cost for no gain. Add retry with backoff on 429/5xx, and respect the rate limit.

</details>

<details><summary><b>Q5.</b> Why does <code>itertools.groupby</code> give you "C001" twice?</summary>

It only groups consecutive equal keys, the way `uniq` does without `sort`. Sort by the same key first, or use a `defaultdict(list)`, which doesn't need ordering.

</details>

<details><summary><b>Q6.</b> Mini design: a 50 GB JSONL file of GPS pings must be loaded to the warehouse from a single 4 GB machine. Sketch the Python.</summary>

A generator reads line by line (`for line in f`) and `json.loads` each line. Skip or dead-letter malformed lines instead of crashing. `batches(..., 10_000)` feeds the loader, so memory stays at one batch. Wrap each batch load in `retry`, and make it idempotent (stage and then `MERGE`, or record the batch offset) so a rerun doesn't duplicate rows. Past a few GB, the better answer is often to upload the file to S3 and `COPY INTO` Snowflake, so Python does no row-by-row work.

</details>

---

## Related

- [python-questions.md](../questions/python-questions.md): language Q&A and typing drills
- [`practical/typing_drills/`](../../practical/typing_drills/): timed exercises
- [python_graphs.py](python_graphs.py): DFS, BFS, topological sort, grids, backtracking
- [rest-apis-webhooks.md](rest-apis-webhooks.md): idempotency keys and retries
- [pyspark.md](../data-engineering/pyspark.md): when the data outgrows one machine
