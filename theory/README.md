# Theory — map of the study material

Interview prep for senior data engineering, system design and Forward Deployed Engineer roles. Everything here renders in the studybook (`node tools/build-studybook.mjs` → `studybook/theory.html`), where docs are grouped by folder and the question bank powers mix mode.

**How to use it:** read a doc once, then close it and answer its **Self-check** out loud. Retrieval practice teaches; rereading doesn't. For drilling, use mix mode (key <kbd>m</kbd>) or `/teacher` in Claude Code.

---

## Folders

| Folder | What lives there | Start with |
| --- | --- | --- |
| [system_design/](system_design/README.md) | The design method, six worked case studies (trucks, loads, invoices), and reference docs for streaming, caches, databases, AWS | [system_design/README.md](system_design/README.md) |
| [cloud/](cloud/architecture-comparison.md) | **The core toolkit** (one default tool per job) and the 10 / 10k / 100k trucks scale ladder | [architecture-comparison.md](cloud/architecture-comparison.md) |
| [software-design/](software-design/) | Design patterns and software architecture styles, kept to the small set that gets asked | [design-patterns.md](software-design/design-patterns.md) |
| [data-engineering/](data-engineering/) | SQL, PySpark, Snowflake performance & cost, Databricks | [sql-advanced.md](data-engineering/sql-advanced.md) |
| [backend/](backend/) | Python, graph algorithms, Node/Express, REST APIs & webhooks, web performance & security | [python-general.md](backend/python-general.md) |
| [frontend/](frontend/) | React and web vocabulary for engineers whose home turf isn't frontend | [frontend-concepts.md](frontend/frontend-concepts.md) |
| [ai/](ai/llm-prompting-and-evals.md) | Working with LLMs: prompting, agents and evals | [llm-prompting-and-evals.md](ai/llm-prompting-and-evals.md) |
| [questions/](questions/README.md) | The Q&A bank: model answers with collapsed reveals, used by mix mode | [questions/README.md](questions/README.md) |

### Every doc

| Doc | What it covers |
| --- | --- |
| **Data engineering** | |
| [sql-advanced.md](data-engineering/sql-advanced.md) | OR-join anti-pattern, NULL traps, anti-joins, window functions, EXPLAIN, isolation levels & MVCC, extracting from a live OLTP database |
| [pyspark.md](data-engineering/pyspark.md) | Driver/executors/partitions, lazy DAG and shuffles, reading `explain()` and the Spark UI, debugging skew and slow jobs, AQE |
| [snowflake-performance.md](data-engineering/snowflake-performance.md) | Micro-partition pruning, Query Profile, spilling, clustering, warehouse sizing, caching layers, cost attribution |
| [databricks.md](data-engineering/databricks.md) | Lakehouse vs DBMS, compute types and DBU pricing, Delta Lake log/time travel/VACUUM, clustering, Unity Catalog, Delta Sharing |
| **Architecture** | |
| [cloud/architecture-comparison.md](cloud/architecture-comparison.md) | Core toolkit on AWS, scale ladder, four reference archetypes, the AWS services in each of the six cases, AWS service per layer |
| [cloud/data-services-glossary.md](cloud/data-services-glossary.md) | Short cards with links: DynamoDB, Firehose, Managed Flink, MSK and MSK Connect, IoT Core (MQTT), Redshift vs Snowflake, plus Fivetran, Airbyte and Confluent Cloud on AWS |
| [99-reference/streaming-tools.md](system_design/99-reference/streaming-tools.md) | Transport vs processor, queue vs log, Lambda vs Flink, event time, watermarks, delivery semantics |
| [99-reference/sql-vs-nosql.md](system_design/99-reference/sql-vs-nosql.md) | Database families, choosing one, dual-write anti-pattern, outbox, CDC, saga, consistency |
| [99-reference/in-memory-databases.md](system_design/99-reference/in-memory-databases.md) | Redis data structures as design tools, caching patterns, invalidation, stampedes, eviction |
| [software-design/design-patterns.md](software-design/design-patterns.md) | Strategy, Factory, Adapter, Decorator, Observer, Repository, Singleton; composition over inheritance, SOLID with a bad → good example per principle |
| [software-design/architecture.md](software-design/architecture.md) | Monolith vs microservices, layered, hexagonal, event-driven, serverless, sync vs async, resilience (timeout, retry, idempotency, circuit breaker) |
| [99-reference/aws-services-map.md](system_design/99-reference/aws-services-map.md) | AWS services by the question they answer, plus reference architectures |
| **Backend & APIs** | |
| [python-general.md](backend/python-general.md) | Type-from-memory templates: group-by, dedup-latest, flatten JSON, chunked reads, retry with backoff, intervals; fumbled signatures; threads vs processes vs asyncio |
| [python_graphs.py](backend/python_graphs.py) | Runnable DFS, BFS, cycle detection, topological sort, Dijkstra, Union-Find, grids, backtracking, with asserts |
| [rest-apis-webhooks.md](backend/rest-apis-webhooks.md) | Status codes, idempotency keys, webhook signing and retries, API key vs OAuth, CORS, pagination |
| [nodejs-express.md](backend/nodejs-express.md) | Middleware pipeline, async error handling, logging, calling third-party APIs, TS/ESM gotchas |
| [performance-and-security.md](backend/performance-and-security.md) | N+1, indexing, caching, Core Web Vitals, XSS, CSRF, SQL injection, JWT and token storage |
| **Frontend** | |
| [react.md](frontend/react.md) | Hooks (the canonical table), effects and the fetch race, StrictMode, memoization, controlled forms, TypeScript discriminated unions |
| [frontend-concepts.md](frontend/frontend-concepts.md) | Hook vs webhook, middleware in three frameworks, components/props/state, CSR vs SSR vs SSG, bundlers |
| **AI** | |
| [llm-prompting-and-evals.md](ai/llm-prompting-and-evals.md) | Using Claude Code in a live interview (Tetris walkthrough, planning with a strong model and building with a cheaper one, PLAN.md), the agent loop, system prompt structure, structured outputs, evals and judge calibration, latency and cost |

---

## Study tracks

Pick the track for the interview in front of you. Each ends in mix mode with the listed question topics.

**A. Data engineering / backend FDE (ETL-heavy)**
1. [sql-advanced.md](data-engineering/sql-advanced.md): the OR-join and OLTP-extraction sections are the most asked
2. [snowflake-performance.md](data-engineering/snowflake-performance.md), then [pyspark.md](data-engineering/pyspark.md) §debugging
3. [cloud/architecture-comparison.md](cloud/architecture-comparison.md) §0 only: the core toolkit and scale ladder
4. Cases: [freight-billing-warehouse](system_design/freight-billing-warehouse/README.md) → [cdc-postgres-to-warehouse](system_design/cdc-postgres-to-warehouse/README.md) → [warehouse-refactor-consolidation](system_design/warehouse-refactor-consolidation/README.md)
5. Mix: `sql`, `snowflake`, `dbt`, `airflow`, `python`, `ownership-troubleshooting`

**B. System design / architecture**
1. [system_design/README.md](system_design/README.md): the method (size → draw → justify → failure modes → summarize)
2. [architecture-comparison.md](cloud/architecture-comparison.md) → [streaming-tools.md](system_design/99-reference/streaming-tools.md) → [sql-vs-nosql.md](system_design/99-reference/sql-vs-nosql.md) → [in-memory-databases.md](system_design/99-reference/in-memory-databases.md)
3. Cases: [truck-stream-processor](system_design/truck-stream-processor/README.md) → [live-load-board](system_design/live-load-board/README.md) → [document-ingestion-pipeline](system_design/document-ingestion-pipeline/README.md)
4. Mix: `system-design`, `streaming`, `databases-caching`

**C. Full-stack + LLM (Forward Deployed Engineer)**
1. [rest-apis-webhooks.md](backend/rest-apis-webhooks.md) → [nodejs-express.md](backend/nodejs-express.md)
2. [frontend-concepts.md](frontend/frontend-concepts.md) if the vocabulary feels shaky, then [react.md](frontend/react.md)
3. [llm-prompting-and-evals.md](ai/llm-prompting-and-evals.md)
4. [performance-and-security.md](backend/performance-and-security.md): the security half is what gets asked
5. Mix: `llm`, `python`, `databases-caching` (API/React questions live in each doc's Self-check for now)

**D. Live coding warm-up** (the failure mode is rusty typing, not logic)
1. [python-general.md](backend/python-general.md) §3 signatures that get fumbled and §6 common mistakes
2. Run [python_graphs.py](backend/python_graphs.py), then re-type each function from memory
3. Typing drills in `practical/typing_drills/` and the `D`-numbered drills in [python-questions.md](questions/python-questions.md)

---

## Commonly fumbled topics → where the answer lives

| Weak spot | Short answer | Doc |
| --- | --- | --- |
| The bad OR-join query | `OR` in a join predicate blocks hash/merge joins, degrades toward nested loops, and can fan out duplicates. Split into two joins + `COALESCE` (dedupe the lookup side first, or it still fans out), or `UNION`. | [sql-advanced.md §1](data-engineering/sql-advanced.md) |
| Reading a production DB without hurting it | Read replica for bulk, log-based CDC for freshness, `updated_at` watermark only when deletes don't matter. | [sql-advanced.md](data-engineering/sql-advanced.md) · [CDC case](system_design/cdc-postgres-to-warehouse/README.md) |
| Why a Spark job is slow or frozen | Spark UI → Stages: one task far slower = skew; many Exchanges = shuffles; high GC = memory; pending tasks = no executors. | [pyspark.md](data-engineering/pyspark.md) |
| Choosing between tools | One default per job, plus the trigger that would make you switch. Size it first. | [architecture-comparison.md §0](cloud/architecture-comparison.md) |
| Graphs and recursion under time pressure | Visited set + recurse on unvisited neighbours; BFS with a deque for shortest path. | [python_graphs.py](backend/python_graphs.py) |

---

## Where each shared concept lives

Several ideas show up in many docs. Each has **one canonical home** with the full explanation; other docs give one line and link there.

| Concept | Canonical home |
| --- | --- |
| Core toolkit, scale ladder | [cloud/architecture-comparison.md](cloud/architecture-comparison.md) (mirrored in `.claude/skills/teacher/SKILL.md`) |
| Queue vs log, Kinesis vs Kafka, delivery semantics, watermarks | [streaming-tools.md](system_design/99-reference/streaming-tools.md) |
| Dual writes, outbox, CDC as a pattern, consistency models | [sql-vs-nosql.md](system_design/99-reference/sql-vs-nosql.md) |
| Extracting from an OLTP database (replica, CDC setup, isolation) | [sql-advanced.md](data-engineering/sql-advanced.md) |
| Caching patterns and invalidation | [in-memory-databases.md](system_design/99-reference/in-memory-databases.md) |
| Pruning, clustering, warehouse cost | [snowflake-performance.md](data-engineering/snowflake-performance.md) |
| Idempotency keys, webhook signing and retries, CORS | [rest-apis-webhooks.md](backend/rest-apis-webhooks.md) |
| React hooks, `useMemo` / `useCallback` / `React.memo` | [react.md](frontend/react.md) |

## Doc conventions

Theory docs follow one shape, adapted to fit and never padded:

1. **TL;DR**: 3–5 quotable lines you could say if interrupted.
2. **The problem**: the pain the concept removes, with numbers, in the trucks/loads/invoices domain where it fits.
3. **The mechanism**: how it actually works, with a diagram where it helps and a bridge from SQL/Spark/Snowflake.
4. **Decide**: "pick X when ___, switch to Y when ___".
5. **Failure modes and common wrong answers**.
6. **Self-check**: questions with answers hidden in `<details>`.
7. **Related**: links to the canonical homes above.

Worked examples refer to two running projects kept outside this repo — a **reference API** (Express/TypeScript, wrapping a legacy service) and a **reference dashboard** (Vite + React) — named as external and never linked with relative paths. Figures for pricing, limits and versions are labelled *approx.* with the date checked.
