/* ============================================================
   Advisor — you pick the business needs and it returns
   la arquitectura recomendada (no te pregunta: te responde).
   Se monta sobre el shell del visor igual que mix.js: reusa #doc,
   buildToc(), renderMermaid() y openDoc().
   ============================================================ */
(function () {
  const q$ = (s, r = document) => r.querySelector(s);
  const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const KEY = "ip-advisor";
  const read = () => { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch { return {}; } };
  const save = v => { try { localStorage.setItem(KEY, JSON.stringify(v)); } catch {} };

  /* ---------------- preguntas ---------------- */
  const QUESTIONS = [
    { id: "fleet", label: "Fleet size", opts: [
      ["s", "~10 trucks"], ["m", "~500 trucks"], ["l", "~10,000 trucks"], ["xl", "100,000+ trucks"]] },
    { id: "latency", label: "How fresh must the data be?", opts: [
      ["batch", "Next day is fine"], ["minutes", "Within minutes"],
      ["seconds", "Seconds (live map)"], ["subsecond", "Sub-second (instant alerts)"]] },
    { id: "sources", label: "What data does the business have?", multi: true, opts: [
      ["sql", "Transactional SQL (orders, billing)"], ["nosql", "NoSQL app data (Mongo / DynamoDB)"],
      ["marketing", "Marketing & CRM SaaS (HubSpot, Ads, Salesforce)"], ["telemetry", "GPS / ELD truck telemetry"],
      ["docs", "Documents (BOL, POD, invoices)"], ["webhooks", "Partner APIs & webhooks"]] },
    { id: "uses", label: "Who consumes it?", multi: true, opts: [
      ["bi", "BI dashboards & reporting"], ["livemap", "Live operations map"],
      ["alerts", "Real-time alerts (late, offline, geofence)"], ["api", "Customer tracking API"],
      ["ml", "ML / AI (ETA, pricing, LLM agents)"]] },
    { id: "cloud", label: "Cloud", opts: [
      ["aws", "AWS"], ["gcp", "GCP"], ["azure", "Azure"], ["any", "Undecided / multi-cloud"]] },
    { id: "team", label: "Team", opts: [
      ["small", "1–2 generalist engineers"], ["sql", "Data team, SQL / dbt first"],
      ["platform", "Platform team (Spark / Kafka experience)"]] },
    { id: "budget", label: "Budget", opts: [
      ["tight", "Tight"], ["moderate", "Moderate"], ["enterprise", "Enterprise"]] },
    { id: "compliance", label: "Compliance", opts: [
      ["none", "Nothing special"], ["pii", "PII / GDPR"], ["regulated", "Regulated (SOC 2, HIPAA, residency)"]] }
  ];

  const PRESETS = [
    { name: "Startup · 10 trucks", pick: { fleet: "s", latency: "minutes", sources: ["sql", "telemetry"], uses: ["bi"],
      cloud: "aws", team: "small", budget: "tight", compliance: "none" } },
    { name: "Regional carrier · 500 trucks + marketing", pick: { fleet: "m", latency: "minutes",
      sources: ["sql", "nosql", "marketing", "telemetry"], uses: ["bi", "livemap"], cloud: "aws", team: "sql",
      budget: "moderate", compliance: "pii" } },
    { name: "Marketing + SQL + NoSQL (no streaming)", pick: { fleet: "m", latency: "batch",
      sources: ["sql", "nosql", "marketing"], uses: ["bi", "ml"], cloud: "gcp", team: "sql", budget: "moderate", compliance: "pii" } },
    { name: "National fleet · 10k trucks", pick: { fleet: "l", latency: "seconds",
      sources: ["sql", "telemetry", "docs", "webhooks"], uses: ["bi", "livemap", "alerts", "api"], cloud: "aws",
      team: "platform", budget: "moderate", compliance: "pii" } },
    { name: "Enterprise · 100k trucks", pick: { fleet: "xl", latency: "subsecond",
      sources: ["sql", "nosql", "marketing", "telemetry", "docs", "webhooks"], uses: ["bi", "livemap", "alerts", "api", "ml"],
      cloud: "any", team: "platform", budget: "enterprise", compliance: "regulated" } }
  ];

  /* ---------------- catalogue by cloud ---------------- */
  const SVC = {
    aws: { name: "AWS", fn: "Lambda", queue: "SQS", log: "Kinesis Data Streams (on-demand)", kafka: "Amazon MSK",
      flink: "Managed Service for Apache Flink", delivery: "Kinesis Firehose", obj: "S3", pg: "Aurora PostgreSQL",
      kv: "DynamoDB", cache: "ElastiCache (Valkey)", cdc: "AWS DMS", sched: "EventBridge Scheduler",
      airflow: "MWAA (managed Airflow)", workflow: "Step Functions", ocr: "Textract", llm: "Bedrock",
      ws: "API Gateway WebSocket", api: "API Gateway (HTTP) + Lambda", iot: "IoT Core", mon: "CloudWatch",
      secrets: "Secrets Manager + KMS", private: "VPC endpoints / PrivateLink", nosqlCdc: "DynamoDB Streams",
      dwNative: "Redshift", notify: "SNS" },
    gcp: { name: "GCP", fn: "Cloud Run functions", queue: "Pub/Sub", log: "Pub/Sub", kafka: "Managed Service for Apache Kafka",
      flink: "Dataflow (Apache Beam)", delivery: "Pub/Sub BigQuery subscription", obj: "Cloud Storage",
      pg: "Cloud SQL for PostgreSQL", kv: "Firestore / Bigtable", cache: "Memorystore", cdc: "Datastream",
      sched: "Cloud Scheduler", airflow: "Cloud Composer (Airflow)", workflow: "Workflows", ocr: "Document AI",
      llm: "Vertex AI", ws: "Cloud Run (WebSockets)", api: "Cloud Run + API Gateway", iot: "Pub/Sub ingest API",
      mon: "Cloud Monitoring", secrets: "Secret Manager + Cloud KMS", private: "Private Service Connect / VPC-SC",
      nosqlCdc: "Firestore triggers (Eventarc)", dwNative: "BigQuery", notify: "Pub/Sub push" },
    azure: { name: "Azure", fn: "Azure Functions", queue: "Service Bus", log: "Event Hubs", kafka: "Event Hubs (Kafka API)",
      flink: "Azure Stream Analytics", delivery: "Event Hubs Capture", obj: "ADLS Gen2",
      pg: "Azure Database for PostgreSQL", kv: "Cosmos DB", cache: "Azure Cache for Redis", cdc: "Debezium on Event Hubs",
      sched: "Functions timer trigger", airflow: "Azure Data Factory", workflow: "Durable Functions",
      ocr: "Document Intelligence", llm: "Azure OpenAI", ws: "Web PubSub", api: "API Management + Functions",
      iot: "IoT Hub", mon: "Azure Monitor", secrets: "Key Vault", private: "Private Link",
      nosqlCdc: "Cosmos DB change feed", dwNative: "Microsoft Fabric", notify: "Event Grid" },
    any: { name: "multi-cloud", fn: "Containers (Kubernetes / Cloud Run-style)", queue: "RabbitMQ or the cloud queue",
      log: "Kafka (Confluent Cloud)", kafka: "Confluent Cloud", flink: "Confluent Cloud for Apache Flink",
      delivery: "Kafka Connect sink", obj: "Object storage (S3 API)", pg: "Managed PostgreSQL", kv: "MongoDB Atlas / ScyllaDB",
      cache: "Redis / Valkey", cdc: "Debezium", sched: "Kubernetes CronJob", airflow: "Astronomer (Airflow) or Dagster",
      workflow: "Temporal", ocr: "OCR / vision model", llm: "Model API behind a gateway", ws: "WebSocket service",
      api: "Containerized API + gateway", iot: "MQTT broker (EMQX / HiveMQ)", mon: "Datadog / Grafana",
      secrets: "HashiCorp Vault", private: "PrivateLink per provider", nosqlCdc: "Debezium / Mongo change streams",
      dwNative: "Snowflake", notify: "Kafka topic → notifier" }
  };
  const TRUCKS = { s: 10, m: 500, l: 10000, xl: 100000 };
  const short = x => x.split(/ \(| \/ | \+ | or /)[0];
  const fmt = n => n >= 100 ? Math.round(n).toLocaleString("en-US") : n >= 1 ? n.toFixed(1) : n.toFixed(2);

  /* ---------------- glossary (only the terms that appear are shown) ---------------- */
  const GLOSSARY = [
    ["CDC", "Change Data Capture. Reads the database's internal change log, so every insert, update and delete is copied elsewhere without querying the tables."],
    ["Fivetran", "Paid service with ready-made connectors that copy data from apps and databases into a warehouse."],
    ["Airbyte", "Open-source alternative to Fivetran. Cheaper, can run in your own network, needs more upkeep."],
    ["Lambda", "AWS function: a small piece of code that runs when something happens (a request, a message). No servers to manage."],
    ["functions", "Small pieces of code the cloud runs on demand, per request or message. No servers to manage."],
    ["Kinesis", "AWS's managed event pipe. Keeps events for days so several systems can read them independently."],
    ["Kafka", "Open-source event pipe. Very high throughput, many readers, keeps events as long as you want. More work to operate."],
    ["Pub/Sub", "Google Cloud's managed messaging and event pipe."],
    ["Event Hubs", "Azure's managed event pipe; speaks the Kafka protocol."],
    ["Flink", "Engine that processes events continuously and remembers state per key (e.g. last ping per truck), with timers."],
    ["Spark", "Distributed engine for big data (PySpark). Streaming mode processes events in small batches."],
    ["shards", "Slices of a Kinesis stream. Each takes ~1 MB/s; events for the same truck always go to the same shard, so they stay in order."],
    ["partitions", "Slices of a Kafka topic, read in parallel. Events with the same key stay in order."],
    ["Snowflake", "Cloud data warehouse: stores data in columns for fast analytical SQL. Runs on AWS, GCP and Azure."],
    ["BigQuery", "Google's serverless data warehouse; you pay per query."],
    ["Redshift", "AWS's native data warehouse."],
    ["Databricks", "Platform for Spark, SQL and ML on top of files in cloud storage (a \"lakehouse\")."],
    ["Iceberg", "Open table format for files on S3/GCS. Any engine (Snowflake, Spark, Athena) can read the same data."],
    ["dbt", "Tool to build warehouse tables from SQL files kept in Git, with tests and documentation."],
    ["marts", "The final, clean tables that dashboards and analysts use."],
    ["staging", "Intermediate tables where raw data is cleaned and renamed."],
    ["Airflow", "Scheduler that runs pipeline steps in order, retries failures and re-runs past days."],
    ["Dagster", "Modern alternative to Airflow, organized around the data assets it produces."],
    ["PostGIS", "Postgres extension for maps and locations (distance, \"within 50 miles\")."],
    ["GEO index", "Index that answers \"which points are near here?\" quickly."],
    ["MQTT", "Lightweight messaging protocol designed for millions of small devices."],
    ["webhooks", "When another company's system calls your URL to tell you something happened."],
    ["idempotency", "Processing the same message twice has the same effect as once, so retries don't create duplicates."],
    ["WebSocket", "A connection that stays open so the server can push updates to the browser."],
    ["Terraform", "Infrastructure as code: cloud resources defined in files and reviewed like code."],
    ["PII", "Personally identifiable information: names, phones, emails, addresses."],
    ["read replica", "A read-only, continuously updated copy of the database, for heavy queries."],
    ["source of truth", "The one place where a piece of data is officially stored; everything else is a copy."],
    ["Metabase", "Open-source dashboard and BI tool."],
    ["Step Functions", "AWS service that runs multi-step workflows with retries."],
    ["Textract", "AWS service that reads text and tables from scanned documents."],
    ["Bedrock", "AWS service to call LLMs (e.g. Claude) through one API."]
  ];

  /* ---------------- recommendation engine ---------------- */
  function recommend(s) {
    const C = SVC[s.cloud];
    const sources = s.sources.length ? s.sources : ["sql"];
    const src = k => sources.includes(k), use = k => s.uses.includes(k);
    const tel = src("telemetry");
    const rt = s.latency === "seconds" || s.latency === "subsecond";
    const big = s.fleet === "l" || s.fleet === "xl";
    const lean = s.team === "small" || s.budget === "tight";
    const stateful = use("alerts") || s.latency === "subsecond";

    // --- volumen ---
    const ping = s.latency === "subsecond" ? 5 : s.latency === "seconds" ? 15 : 60;
    const eps = tel ? TRUCKS[s.fleet] / ping : 0;
    const mbps = eps / 1024;                                   // ~1 KB por ping
    const gbDay = eps * 86400 / 1e6;
    const shards = Math.max(1, Math.ceil(Math.max(mbps, eps / 1000)));

    // --- transporte ---
    const needsLog = tel && (rt || big);
    const kafka = needsLog && (s.cloud === "any" ||
      (s.team === "platform" && (s.fleet === "xl" || (s.budget === "enterprise" && s.uses.length >= 4))));
    const busName = kafka ? C.kafka : C.log;

    // --- almacenes ---
    const multiSource = sources.filter(k => !["docs", "webhooks"].includes(k)).length >= 2;
    const needDw = use("bi") || use("ml") || src("marketing") || multiSource;
    const replicaOnly = !needDw || (s.fleet === "s" && s.budget === "tight" && !src("marketing") && !use("ml"));
    const lake = !replicaOnly && ((tel && big) || (s.budget === "enterprise" && (tel || use("ml"))));
    const hotWanted = use("livemap") || use("api") || use("alerts");
    const hot = tel && hotWanted
      ? (big ? `${C.kv} (latest position per truck) + ${short(C.cache)} GEO index` : `${short(C.pg)} truck_latest table (UPSERT) + PostGIS`)
      : null;
    const connector = s.budget === "tight" || s.compliance === "regulated" ? "Airbyte" : "Fivetran";
    const sqlCdc = src("sql") && !replicaOnly && (rt && hotWanted || s.fleet === "xl");
    const cdcTool = kafka ? "Debezium (Kafka Connect)" : C.cdc;
    const simpleOrch = !replicaOnly && !big && s.budget !== "enterprise" && (lean || sources.length <= 3);
    const dbtKind = s.team === "sql" && !lean ? "Cloud" : "Core";

    let dw;
    if (replicaOnly) dw = { kind: "replica", short: "Postgres read replica", pick: `${C.pg} read replica`,
      why: "A read-only copy of the production database. Analysts can run heavy queries without slowing down the app.",
      alts: [["A data warehouse", "With only one data source there's nothing to combine yet. It would be cost without value."]] };
    else if (s.cloud === "gcp") dw = { kind: "bq", short: "BigQuery", pick: "BigQuery",
      why: "Google's warehouse: no servers to manage, pay per query, and it connects natively to the other GCP services.",
      alts: [["Snowflake", "Also great, but on GCP BigQuery is already wired into your accounts, permissions and billing."]] };
    else if (s.team === "platform" && (s.fleet === "xl" || use("ml"))) dw = { kind: "lakehouse", short: "Databricks lakehouse",
      pick: `Databricks (data kept as Delta / Iceberg files on ${short(C.obj)})`,
      why: "Your team knows Spark and needs ML. Data stays as open files on cheap storage, queried with SQL or Python.",
      alts: [["Snowflake", "Great for SQL reports, but ML and huge data volumes are cheaper to run next to the files."]] };
    else dw = { kind: "snowflake", short: "Snowflake", pick: "Snowflake",
      why: "The easiest warehouse for SQL teams: each team gets its own compute, it handles NoSQL JSON, it can hide personal data per role, and it runs on any cloud.",
      alts: [[C.dwNative, s.cloud === "aws" ? "Needs more tuning. Only pick it if the company requires AWS-only services."
        : s.cloud === "azure" ? "A good fit for Microsoft-heavy BI shops, but less mature with dbt." : "Ties you to one cloud."]] };

    // --- procesamiento ---
    let proc = null;                                            // {kind, pick, rows, alts}
    if (tel && !rt && needsLog) proc = { kind: "micro", pick: `${C.delivery} → ${C.obj}`,
      rows: [
        { what: "Saving history", use: `${short(C.delivery)} groups events into files on ${short(C.obj)}, loaded into the warehouse every few minutes`,
          why: "Nobody needs this data within seconds, so batching it is the cheapest option." },
        hotWanted && { what: "Latest position", use: `A ${short(C.fn)} updates each truck's last position`,
          why: "The map and API only need the newest ping per truck." }
      ].filter(Boolean),
      alts: [["Flink or Spark streaming", "Built for second-level reactions that nobody here needs."]] };
    else if (tel && rt && (s.latency === "subsecond" || (stateful && big)))
      proc = { kind: "flink", pick: kafka && s.cloud !== "any" ? `Flink on ${short(C.kafka)}` : C.flink,
        rows: [
          { what: "Engine", use: kafka && s.cloud !== "any" ? `Flink on ${short(C.kafka)} (or ${C.flink})` : C.flink,
            why: "Remembers state per truck (like the time of its last ping) and fires a timer when a truck goes silent. After a crash it resumes without losing or double-counting events." },
          { what: "Load", use: `~${fmt(eps)} events per second`,
            why: "Too many to run one function per event. Flink processes the stream continuously on a small cluster." }
        ],
        alts: [["Lambda / functions", "They forget everything between events and get expensive at this volume."],
               ["Spark streaming", "Works in small batches, so alerts arrive a few seconds later."]] };
    else if (tel && rt && s.team === "platform" && big)
      proc = { kind: "spark", pick: "Spark Structured Streaming",
        rows: [{ what: "Engine", use: "Spark Structured Streaming (Databricks)",
          why: "Your team already writes PySpark, and a few seconds of delay is fine for this business." }],
        alts: [["Flink", "Slightly faster, but a new tool to learn with no business gain here."]] };
    else if (tel && (rt || s.fleet !== "s"))
      proc = { kind: "fn", pick: `${C.fn}`,
        rows: [
          { what: "Each ping", use: needsLog ? `A ${short(C.fn)} reads from the event pipe` : `A ${short(C.fn)} runs once per ping`,
            why: `Checks the data, drops duplicates and saves the truck's latest position. ~${fmt(eps)} events per second is easy for functions.` },
          use("alerts") && { what: "Alerts", use: "A query that runs every minute",
            why: "Finds trucks with no ping in the last 30 minutes. Simple, and no streaming engine needed." }
        ].filter(Boolean),
        alts: [["Flink", "A whole cluster for work a small function already handles."]] };

    const layers = [];

    // 1. ingesta
    const ing = [];
    if (tel) ing.push(s.fleet === "xl"
      ? { what: "Truck GPS", use: `Devices connect to ${C.iot}${/MQTT/.test(C.iot) ? "" : " over MQTT"} (or the tracking vendor's webhooks)`,
          why: "At 100k trucks you want a broker built for millions of small device messages." }
      : { what: "Truck GPS", use: `The tracking vendor (Samsara, Motive) sends pings to a small endpoint: ${C.api}`,
          why: "You usually don't own the GPS devices. The vendor pushes the data to a URL you host." });
    if (src("sql")) ing.push(replicaOnly
      ? { what: "Orders & billing (SQL)", use: "Nothing to copy. Reports read a replica of this same database",
          why: "With one database and a few reports, moving data elsewhere adds cost without benefit." }
      : sqlCdc
      ? { what: "Orders & billing (SQL)", use: `${cdcTool} reads the database's change log (CDC)`,
          why: "Every insert, update and delete arrives within seconds, without slowing down the production database." }
      : { what: "Orders & billing (SQL)", use: `${connector} copies new and changed rows every ~15 minutes`,
          why: "Reports don't need second-by-second data, and a ready-made connector means no code to maintain." });
    if (src("nosql")) ing.push(needsLog && rt
      ? { what: "App data (NoSQL)", use: `${kafka ? "Debezium" : C.nosqlCdc} sends every change into the event pipe`,
          why: "The live views need app changes within seconds." }
      : { what: "App data (NoSQL)", use: `${connector}'s built-in connector`,
          why: "Same tool as the other sources, so all the copying is managed in one place." });
    if (src("marketing")) ing.push({ what: "Marketing & CRM", use: `${connector}, every hour or day`,
      why: "Marketing APIs only allow a few calls per minute, return data page by page, and change past numbers later (late conversions). The connector handles all of that." });
    if (src("docs")) ing.push({ what: "Documents", use: `Upload to ${short(C.obj)} → ${short(C.workflow)} runs the steps → ${short(C.ocr)} reads the text → ${short(C.llm)} extracts the fields`,
      why: "Keep the original file, and send low-confidence results to a person to review." });
    if (src("webhooks")) ing.push({ what: "Partner webhooks", use: `${short(C.api)} replies "OK" immediately, puts the message in ${short(C.queue)}, and a ${short(C.fn)} processes it`,
      why: "Partners retry when you're slow, so answer fast and ignore duplicates (idempotency key)." });
    const ingAlts = [];
    if (src("marketing") || (src("sql") && !replicaOnly && !sqlCdc)) {
      ingAlts.push(["Writing your own Python scripts", "Every time an API changes or blocks you for calling too often, the pipeline breaks and you get paged."]);
      ingAlts.push(connector === "Fivetran"
        ? ["Airbyte", "Cheaper, but you spend more time fixing it. At this budget, paying for less maintenance is worth it."]
        : ["Fivetran", s.compliance === "regulated" ? "Your data would pass through a third-party service. Airbyte can run inside your own network."
                                                     : "Much more expensive for a tight budget. Airbyte does the same job with a bit more maintenance."]);
    }
    layers.push({ layer: "Getting the data in", ask: "How does each kind of data reach your systems?", rows: ing, alts: ingAlts });

    // 2. transporte
    if (needsLog) layers.push({ layer: "Moving the events", ask: "Is there a pipe that carries events between systems?",
      rows: kafka ? [
        { what: "Event pipe", use: busName,
          why: `~${fmt(eps)} events per second read by many systems. Kafka keeps every event, so any system can re-read it, and it works on any cloud.` },
        { what: "Size", use: `${Math.max(6, shards * 3)}+ partitions`,
          why: "Partitions let readers work in parallel. Events for the same truck stay in order." }
      ] : [
        { what: "Event pipe", use: busName,
          why: `It keeps events for days, so several systems (${[proc && "processing", lake || !replicaOnly ? "history" : "", use("livemap") && "live map"].filter(Boolean).join(", ")}) can each read them at their own pace. Nothing to install or run.` },
        { what: "Size", use: s.cloud === "gcp" ? "Scales automatically" : `${shards * 2} ${s.cloud === "aws" ? "shards" : "partitions"}`,
          why: s.cloud === "gcp" ? `~${fmt(mbps)} MB/s of data, and Pub/Sub adjusts capacity itself.` : `~${fmt(mbps)} MB/s of data. Each slice takes about 1 MB/s; doubled to absorb spikes.` }
      ],
      alts: kafka
        ? [[short(SVC[s.cloud === "any" ? "aws" : s.cloud].log), "Has capacity limits per slice and gets costly when many systems read the same data."]]
        : [["Kafka", `Powerful but heavy to operate. At ${fmt(mbps)} MB/s it's extra work for no gain.`],
           [C.queue, "A queue deletes a message once it's read, so only one system could use each event."]] });
    else if (tel) layers.push({ layer: "Moving the events", ask: "Is there a pipe that carries events between systems?",
      rows: [
        { what: "Event pipe", use: "None needed",
          why: `${fmt(eps)} events per second is ${eps < 1 ? "less than one per second" : "a tiny load"}. A function writes each ping straight into the database.` },
        src("webhooks") && { what: "Partner webhooks", use: C.queue, why: "A simple queue absorbs bursts and retries failed messages." }
      ].filter(Boolean),
      alts: [["Kafka or a streaming service", "Adds cost and moving parts with no benefit at this size."]] });
    else if (src("webhooks") || src("docs")) layers.push({ layer: "Moving the events", ask: "Is there a pipe that carries events between systems?",
      rows: [{ what: "Background work", use: C.queue, why: "A queue holds work until a worker is free and retries failures." }],
      alts: [["Kafka", "There's no stream of events to replay. A queue is enough."]] });

    // 3. procesamiento
    if (proc) layers.push({ layer: "Processing live events", ask: "What reacts to each event as it arrives?", rows: proc.rows, alts: proc.alts });

    // 4. operacional
    const op = [];
    const pgHolds = [src("sql") && "orders, billing", src("docs") && "documents", src("webhooks") && "partner events",
                     tel && !needsLog && !hot && "truck pings"].filter(Boolean);
    if (pgHolds.length) op.push({ what: "Business records", use: `${C.pg} (${pgHolds.join(", ")})`,
      why: "The single source of truth. Every other copy is filled from here, never by writing to two places at once." });
    if (src("nosql")) op.push({ what: "App data", use: `${C.kv} (keep it)`,
      why: "Fine for the app, but bad for reports. Reports go to the analytics layer." });
    if (hot && big) op.push({ what: "Latest truck positions", use: hot,
      why: `One record per truck, overwritten on every ping. The GEO index answers "which trucks are near this city?".` });
    else if (hot) op.push({ what: "Latest truck positions", use: `A truck_latest table in ${short(C.pg)} (+ PostGIS for maps)`,
      why: "One row per truck, overwritten on every ping. No extra database needed at this size." });
    if (op.length) layers.push({ layer: "Where the app data lives", ask: "Which databases does the live product read and write?", rows: op,
      alts: hot && big ? [["Postgres for positions", `~${fmt(eps)} updates per second would overload it.`]] : [] });

    // 5. analytics
    layers.push({ layer: "Where analysis happens", ask: "Where do reports and analysts query the data?",
      rows: [
        { what: "Reports & analysis", use: dw.pick, why: dw.why },
        lake && dw.kind !== "lakehouse" && { what: "Raw history", use: `Iceberg files on ${short(C.obj)}`,
          why: `Cheap storage for every raw event${tel ? ` (~${fmt(gbDay)} GB/day)` : ""}. Any tool can read it, and you can rebuild anything from it.` }
      ].filter(Boolean),
      alts: dw.alts });

    // 6. transformation
    if (!replicaOnly) layers.push({ layer: "Cleaning & combining", ask: "How does raw data become trustworthy tables?",
      rows: [
        { what: "Tool", use: `dbt ${dbtKind}`,
          why: "SQL files in Git that build clean tables, with automatic tests (no duplicates, no missing values, data is fresh)." },
        { what: "Layers", use: "raw → staging → marts",
          why: "Raw copies stay untouched, staging cleans them, and marts are the final tables reports use." },
        src("nosql") && { what: "NoSQL documents", use: "Flattened into columns in staging", why: "Reports need rows and columns, not nested JSON." },
        src("marketing") && { what: "One customer view", use: "A single customer table",
          why: "Matches the same company across CRM, billing and the app (by email domain or tax ID), so you can answer: which campaign brought paying customers?" },
        tel && { what: "Truck pings", use: "Rolled up into trips and stop times",
          why: "Nobody reports on raw pings. They report on trips, delays and time waiting at docks." }
      ].filter(Boolean),
      alts: [["Stored procedures or notebooks", "No tests, no version history, and only the person who wrote them understands them."]] });

    // 7. orchestration
    const orch = replicaOnly
      ? { rows: [{ what: "Jobs", use: C.sched, why: "Just a few timed jobs with no dependencies between them." }],
          alts: [["Airflow", "Nothing to coordinate yet."]] }
      : simpleOrch
      ? { rows: [{ what: "Jobs", use: `${connector}'s own schedule, then dbt ${dbtKind === "Cloud" ? "Cloud jobs" : "Core run from CI"}`,
            why: "Only two steps: copy the data, then build the tables. Their built-in schedulers are enough." }],
          alts: [["Airflow", "Add it once 3 or more tools depend on each other."]] }
      : { rows: [{ what: "Jobs", use: C.airflow + (s.cloud !== "any" ? " or Dagster" : ""),
            why: "Many sources and steps need one place that runs them in order, retries failures, re-runs past days, and alerts when something is late." }],
          alts: [["Cron or each tool's own scheduler", "No view of what depends on what, and failures happen silently."]] };
    if (src("docs")) orch.rows.push({ what: "Each document", use: C.workflow, why: "Runs the steps for each file (read → extract → review → save), with retries." });
    layers.push({ layer: "Scheduling", ask: "What runs the jobs in the right order?", ...orch });

    // 8. serving
    const bi = s.budget === "tight" ? "Metabase" : s.cloud === "gcp" ? "Looker" : s.cloud === "azure" ? "Power BI" : s.budget === "enterprise" ? "Tableau or Sigma" : "Metabase or Sigma";
    const serve = [
      use("bi") && { what: "Dashboards", use: bi, why: s.budget === "tight" ? "Free and open source." : `Fits the ${C.name} setup and the budget.` },
      use("livemap") && { what: "Live map", use: `Load a snapshot, then receive updates through ${short(C.ws)}`,
        why: "The server pushes only what changed, instead of every screen asking again every few seconds." },
      use("api") && { what: "Customer tracking", use: `${short(C.api)} with a ${short(C.cache)} cache`,
        why: "Customer traffic never touches the production database." },
      use("alerts") && { what: "Alerts", use: `${proc && ["flink", "spark"].includes(proc.kind) ? short(proc.pick) : "Scheduled query"} → ${C.notify}`,
        why: "Dispatchers get notified when a truck is late, offline or leaves its zone." },
      use("ml") && { what: "ML / AI", use: `Clean warehouse tables + ${short(C.llm)}`,
        why: "Models learn from the same trusted tables the reports use." }
    ].filter(Boolean);
    if (serve.length) layers.push({ layer: "Who uses it", ask: "How does each consumer get the data?", rows: serve, alts: [] });

    // 9. seguridad
    const masking = dw.kind === "bq" ? "Policy tags" : dw.kind === "lakehouse" ? "Unity Catalog column masks" : dw.kind === "snowflake" ? "Masking policies" : "Column-level permissions";
    const sec = [
      { what: "Passwords & keys", use: C.secrets, why: "Never stored in code, and rotated automatically." },
      { what: "Monitoring", use: [C.mon, needsLog && "alarm when readers fall behind", !replicaOnly && "dbt freshness tests"].filter(Boolean).join(" + "),
        why: "You hear about a stuck pipeline before the business does." },
      { what: "Infrastructure", use: "Terraform", why: "Everything is defined as code, so it's reviewed and reproducible." },
      s.compliance !== "none" && { what: "Personal data", use: `${masking} + a deletion process`,
        why: "Only allowed roles see names and phones, and deletion requests reach every copy (GDPR)." },
      s.compliance === "regulated" && { what: "Regulated data", use: `${C.private}, your own encryption keys, audit logs, fixed region`,
        why: `Data never crosses the public internet and every access is recorded${connector === "Airbyte" ? ". Airbyte runs inside your own network" : ""}.` }
    ].filter(Boolean);
    layers.push({ layer: "Security & monitoring", ask: "How do you keep it safe and know when it breaks?", rows: sec, alts: [] });

    // --- what you avoid / when you would switch ---
    const avoid = [];
    if (tel && !needsLog) avoid.push(`A Kafka/Flink setup for ${TRUCKS[s.fleet].toLocaleString("en-US")} trucks. ${fmt(eps)} events per second fits in one database table.`);
    if (!rt && tel) avoid.push("Real-time processing when people only look at the data minutes or a day later.");
    if (src("sql") && (use("bi") || use("ml"))) avoid.push("Running dashboards against the production database. Heavy queries slow down the app.");
    if (src("marketing")) avoid.push("Writing your own scripts to pull HubSpot / Google Ads data.");
    if (src("nosql")) avoid.push("Running reports directly on DynamoDB / Mongo.");
    if (proc && proc.kind === "flink" && big) avoid.push("Using Lambda for alerts that need to remember past events at this volume.");
    if (needsLog && !kafka) avoid.push("Running Kafka yourself without a team dedicated to it.");
    avoid.push("Having the app write the same data to two databases. They drift apart; copy changes from one source instead (CDC).");

    const triggers = [];
    if (tel && !needsLog) triggers.push(`~1,000+ trucks, or a second system needing live data → add ${short(C.log)} as an event pipe.`);
    if (needsLog && !kafka) triggers.push(`Many teams reading the same events, or leaving ${C.name} → move to Kafka (${s.cloud === "any" ? "Confluent" : C.kafka}).`);
    if (proc && proc.kind === "fn") triggers.push(`Alerts that must remember past events at large scale → ${C.flink}.`);
    if (proc && proc.kind === "micro") triggers.push("The business needs second-level updates (live map, alerts) → add a streaming engine.");
    if (replicaOnly) triggers.push("A second data source, or analysts slowing down the replica → a warehouse (Snowflake / BigQuery) + dbt.");
    if (simpleOrch) triggers.push("3 or more tools depending on each other → Airflow or Dagster.");
    if (!lake && tel && !replicaOnly) triggers.push(`Raw truck history gets expensive in the warehouse → keep it as Iceberg files on ${short(C.obj)}.`);
    if (s.compliance === "none") triggers.push("The first big customer asks for SOC 2 → add data masking, audit logs, private networking.");

    // --- encabezado y pitch ---
    const archetype = replicaOnly && !needsLog ? "Keep it simple: functions + Postgres"
      : !needsLog ? "Connectors + warehouse + dbt"
      : kafka ? "Kafka-based streaming platform"
      : `${C.name} managed streaming + ${dw.short}`;
    const fresh = { batch: "next-day", minutes: "minute-level", seconds: "seconds-level", subsecond: "sub-second" }[s.latency];
    const cost = [["$100–500", "$300–1k", "$1k–3k"], ["$1k–4k", "$3k–8k", "$5k–15k"],
                  ["$5k–15k", "$10k–30k", "$20k–60k"], ["$30k–80k", "$60k–150k", "$100k+"]]
                 [["s", "m", "l", "xl"].indexOf(s.fleet)][["tight", "moderate", "enterprise"].indexOf(s.budget)];

    const pitch = [
      `With ${TRUCKS[s.fleet].toLocaleString("en-US")} trucks and ${fresh} freshness${tel ? `, telemetry is about ${fmt(eps)} events per second (${fmt(gbDay)} GB/day)` : ", there's no high-volume stream"}, so ${!needsLog ? "a streaming platform would be over-engineering" : kafka ? "a shared Kafka backbone pays for itself" : `a managed event pipe, ${short(C.log)}, is the right size`}.`,
      `${src("marketing") || multiSource ? `The harder problem is combining ${sources.filter(k => ["sql", "nosql", "marketing"].includes(k)).map(k => ({ sql: "SQL", nosql: "NoSQL", marketing: "marketing" }[k])).join(", ")} data, so I'd use managed connectors${sqlCdc ? " plus CDC" : ""} into ${dw.short}${replicaOnly ? "" : " and build one customer view in dbt"}.` : `Data lands in ${dw.short}.`}${proc ? ` ${short(proc.pick)} handles the ${proc.kind === "micro" ? "batched delivery" : "live path"}.` : ""}`,
      `The trade-off I'm choosing: ${kafka ? "more operational work in exchange for throughput, replay and portability" : lean ? "managed services over control. Less to operate for a small team, at the price of some lock-in" : "managed cloud services and low ops over portability, with data kept in open formats"}.`,
      triggers.length ? `I'd revisit it when: ${triggers[0].charAt(0).toLowerCase() + triggers[0].slice(1)}` : ""
    ].filter(Boolean);

    return { C, s, sources, tel, eps, mbps, gbDay, shards, needsLog, kafka, busName, proc, dw, lake, hot,
             sqlCdc, connector, replicaOnly, layers, avoid, triggers, archetype, cost, pitch, bi };
  }

  /* ---------------- diagrama mermaid ---------------- */
  function diagram(r) {
    const { C, s, sources } = r;
    const src = k => sources.includes(k), use = k => s.uses.includes(k);
    const nodes = new Map(), edges = new Set();
    const clean = t => String(t).replace(/"/g, "'");
    const N = (id, label, db) => { if (!nodes.has(id)) nodes.set(id, db ? `${id}[("${clean(label)}")]` : `${id}["${clean(label)}"]`); return id; };
    const E = (a, b, lbl) => edges.add(lbl ? `${a} -->|${clean(lbl)}| ${b}` : `${a} --> ${b}`);

    const PG = () => N("PG", `<b>${short(C.pg)}</b><br/>source of truth`, true);
    const DW = () => r.replicaOnly ? N("DW", "<b>Read replica</b>", true)
      : N("DW", `<b>${r.dw.short}</b><br/>raw · staging · marts · dbt`, true);
    const CON = () => N("CON", `<b>${r.connector}</b>`);
    const BUS = () => N("BUS", `<b>${short(r.busName)}</b>`);
    const HOT = () => r.hot ? N("HOT", r.hot.startsWith(short(C.pg)) ? "<b>truck_latest</b><br/>PostGIS" : `<b>${short(C.kv)}</b> + ${short(C.cache)}<br/>latest position`, true) : PG();

    if (r.tel) {
      const T = N("T", "Trucks<br/>GPS · ELD");
      const I = N("TI", short(s.fleet === "xl" ? C.iot : C.api));
      E(T, I);
      if (r.needsLog) {
        E(I, BUS());
        if (r.proc && r.proc.kind === "micro" && r.hot) {
          const F = N("FN", short(C.fn));
          E(BUS(), F); E(F, HOT());
        }
        if (r.proc && r.proc.kind !== "micro") {
          const P = N("PR", `<b>${short(r.proc.pick)}</b>`);
          E(BUS(), P);
          if (r.hot) E(P, HOT());
          if (use("alerts") && r.proc.kind !== "fn") E(P, N("AL", "Alerts"));
        }
        if (r.lake) { E(BUS(), N("DL", short(C.delivery))); E("DL", N("RAW", `Iceberg on ${short(C.obj)}`, true)); E("RAW", DW()); }
        else if (!r.replicaOnly) { E(BUS(), N("DL", short(C.delivery))); E("DL", DW()); }
      } else {
        const F = N("FN", short(C.fn));
        E(I, F); E(F, r.hot ? HOT() : PG());
        if (r.hot) E(HOT(), PG());
      }
    }
    if (src("sql")) {
      const D = PG();
      if (r.replicaOnly) E(D, DW(), "replication");
      else if (r.sqlCdc) { if (r.needsLog) E(D, BUS(), "CDC"); else E(D, DW(), "CDC"); }
      else { E(D, CON()); }
    }
    if (src("nosql")) {
      const NS = N("NS", `${short(C.kv)}<br/>app data`, true);
      if (r.needsLog && ["seconds", "subsecond"].includes(s.latency)) E(NS, BUS(), "change stream"); else E(NS, CON());
    }
    if (src("marketing")) E(N("MK", "Marketing SaaS<br/>CRM · Ads"), CON());
    if (r.needsLog && r.sqlCdc && !nodes.has("DL")) E(BUS(), DW());
    if (src("docs")) { E(N("DOC", "Documents<br/>BOL · POD"), N("WF", short(C.workflow))); E("WF", N("OCR", `${short(C.ocr)} + ${short(C.llm)}`)); E("OCR", PG()); }
    if (src("webhooks")) { E(N("WH", "Partner webhooks"), N("Q", short(C.queue))); E("Q", N("WFN", short(C.fn))); E("WFN", PG()); }
    if (nodes.has("PG") && !r.replicaOnly && !src("sql")) E("PG", CON());
    if (nodes.has("CON")) E("CON", DW());

    if (use("bi")) E(DW(), N("BI", `BI · ${short(r.bi)}`));
    if (use("ml")) E(nodes.has("RAW") ? "RAW" : DW(), N("ML", "ML / AI"));
    if (use("livemap")) E(r.hot ? HOT() : PG(), N("MAP", `Live map<br/>${short(C.ws)}`));
    if (use("api")) E(r.hot ? HOT() : PG(), N("API", "Tracking API"));
    if (use("alerts") && !nodes.has("AL")) E(r.hot ? HOT() : PG(), N("AL", "Alerts<br/>scheduled check"), "every 1 min");

    return ["flowchart LR", ...[...nodes.values()].map(x => "    " + x), ...[...edges].map(x => "    " + x)].join("\n");
  }

  /* ---------------- UI ---------------- */
  const valid = (q, v) => q.opts.some(o => o[0] === v);
  let sel = Object.assign({}, PRESETS[1].pick, read());
  for (const q of QUESTIONS) {
    if (q.multi) sel[q.id] = (Array.isArray(sel[q.id]) ? sel[q.id] : []).filter(v => valid(q, v));
    else if (!valid(q, sel[q.id])) sel[q.id] = PRESETS[1].pick[q.id];
  }

  const isOn = () => !!q$("#doc .adv");

  function openAdvisor() {
    // exitMix(false): the restoring form re-opens the previous document asynchronously,
    // and that continuation would overwrite the advisor painted below.
    if (typeof window.__mixExit === "function") window.__mixExit(false);
    else { const b = q$('#doc .mx-run [data-act="exit"]'); if (b) b.click(); }
    state.current = null;
    document.querySelectorAll(".doc.active").forEach(el => el.classList.remove("active"));
    document.title = "Architecture advisor · Theory";
    q$("#crumb").innerHTML = "<b>🧭 advisor › </b>business needs → architecture";
    q$("#meta").textContent = "";
    history.replaceState(null, "", "#advisor");
    q$("#doc").innerHTML = `
      <div class="adv">
        <h1>🧭 Architecture advisor</h1>
        <p class="lead">Pick what the business looks like. The recommended architecture updates instantly: each step says what to use, why, and why not the alternatives.</p>
        <div class="mx-label" style="margin-top:20px">Scenarios</div>
        <div class="mx-chips" id="adv-presets">
          ${PRESETS.map((p, i) => `<button class="mx-chip" data-preset="${i}">${esc(p.name)}</button>`).join("")}
        </div>
        <div class="adv-form" id="adv-form"></div>
        <div id="adv-out" aria-live="polite"></div>
      </div>`;
    q$("#adv-presets").onclick = e => {
      const b = e.target.closest("[data-preset]");
      if (!b) return;
      sel = JSON.parse(JSON.stringify(PRESETS[+b.dataset.preset].pick));
      update();
      toast("Scenario: " + PRESETS[+b.dataset.preset].name);
    };
    q$("#adv-form").onclick = e => {
      const b = e.target.closest("[data-q]");
      if (!b) return;
      const q = QUESTIONS.find(x => x.id === b.dataset.q);
      if (q.multi) {
        const set = new Set(sel[q.id]);
        set.has(b.dataset.v) ? set.delete(b.dataset.v) : set.add(b.dataset.v);
        sel[q.id] = q.opts.map(o => o[0]).filter(v => set.has(v));
      } else sel[q.id] = b.dataset.v;
      // #adv-form is rebuilt wholesale, so re-focus the chip the user just activated —
      // otherwise focus falls back to <body> and every pick needs a full tab traversal.
      const { q: qid, v } = b.dataset;
      update();
      const again = q$(`#adv-form [data-q="${CSS.escape(qid)}"][data-v="${CSS.escape(v)}"]`);
      if (again) again.focus();
    };
    update();
    q$("#scroller").scrollTop = 0;
  }

  function update() {
    save(sel);
    const matched = PRESETS.findIndex(p => JSON.stringify(p.pick) === JSON.stringify(sel));
    document.querySelectorAll("#adv-presets [data-preset]").forEach(b => b.classList.toggle("on", +b.dataset.preset === matched));

    q$("#adv-form").innerHTML = QUESTIONS.map(q => `
      <div class="adv-q">
        <div class="mx-label">${esc(q.label)}${q.multi ? `<span class="hint">pick all that apply</span>` : ""}</div>
        <div class="mx-chips">
          ${q.opts.map(([v, l]) => {
            const on = q.multi ? sel[q.id].includes(v) : sel[q.id] === v;
            return `<button class="mx-chip${on ? " on" : ""}" aria-pressed="${on}" data-q="${q.id}" data-v="${v}">${esc(l)}</button>`;
          }).join("")}
        </div>
      </div>`).join("");

    const r = recommend(sel);
    const stats = [
      [TRUCKS[sel.fleet].toLocaleString("en-US"), "trucks"],
      r.tel ? [fmt(r.eps), "GPS pings / second"] : ["—", "no truck telemetry"],
      r.tel ? [fmt(r.gbDay), "GB of pings / day"] : [String(r.sources.length), "data sources"],
      r.needsLog ? [short(r.busName), "event pipe"] : ["none", "event pipe needed"],
      [r.cost, "infra / month (rough)"]
    ];

    const layersHtml = r.layers.map((l, i) => `
      <div class="adv-layer">
        <div class="adv-lh"><span class="n">${i + 1}</span>
          <div><h3>${esc(l.layer)}</h3><p class="ask">${esc(l.ask)}</p></div>
        </div>
        <div class="adv-rows">
          <div class="adv-row adv-rowhead"><span>What</span><span>Use</span></div>
          ${l.rows.map(x => `
            <div class="adv-row">
              <span class="w">${esc(x.what)}</span>
              <span class="u">${esc(x.use)}</span>
              <span class="y">${esc(x.why)}</span>
            </div>`).join("")}
        </div>
        ${l.alts.length ? `<div class="adv-alts"><b>Why not…</b><ul>${l.alts.map(([no, because]) =>
          `<li><b>${esc(no)}?</b> ${esc(because)}</li>`).join("")}</ul></div>` : ""}
      </div>`).join("");

    // Solo lo elegido (columna "Use"), no las alternativas descartadas: la lista tiene que ser memorizable.
    const body = r.layers.flatMap(l => l.rows.map(x => x.use)).join(" ");
    const terms = GLOSSARY.filter(([t]) => new RegExp(`(^|[^A-Za-z])${t.replace(/[/]/g, "\\/")}([^A-Za-z]|$)`, "i").test(body));

    q$("#adv-out").innerHTML = `
      ${sel.sources.length ? "" : `<p class="adv-empty">No data source picked. Assuming transactional SQL.</p>`}
      <div class="adv-head">
        <span class="mx-tag">recommended</span><span class="mx-tag soft">${esc(r.C.name)}</span>
        <h2 id="adv-summary">${esc(r.archetype)}</h2>
      </div>
      <div class="adv-stats">${stats.map(([b, l]) => `<div class="adv-stat"><b>${esc(b)}</b><span>${esc(l)}</span></div>`).join("")}</div>

      <h2 id="adv-diagram">Architecture</h2>
      <pre class="mermaid">${esc(diagram(r))}</pre>

      ${terms.length ? `<h2 id="adv-glossary">Remember these words</h2>
      <dl class="adv-gloss">${terms.map(([t, d]) => `<dt>${esc(t)}</dt><dd>${esc(d)}</dd>`).join("")}</dl>` : ""}

      <h2 id="adv-layers">Step by step</h2>
      <div class="adv-layers">${layersHtml}</div>

      <h2 id="adv-pitch">How to say it in the interview</h2>
      <blockquote class="adv-pitch">${r.pitch.map(p => `<p>${esc(p)}</p>`).join("")}</blockquote>

      <h2 id="adv-avoid">What you're deliberately not doing</h2>
      <ul>${r.avoid.map(a => `<li>${esc(a)}</li>`).join("")}</ul>

      <h2 id="adv-change">When you'd change it</h2>
      <ul>${r.triggers.map(a => `<li>${esc(a)}</li>`).join("")}</ul>

      <p style="font-size:12px;color:var(--fg-faint);margin-top:30px">Costs are order-of-magnitude infra estimates (no salaries), assuming ~1 KB per ping. Full comparison tables:
      <a href="#" id="adv-doc">cloud/architecture-comparison.md</a></p>`;

    q$("#adv-doc").onclick = e => { e.preventDefault(); openDoc("cloud/architecture-comparison.md"); };
    if (typeof renderMermaid === "function") renderMermaid();
    if (typeof buildToc === "function") { buildToc(); measureHeadings(); onScroll(true); }
  }

  /* ---------------- entradas ---------------- */
  const btn = document.createElement("button");
  btn.id = "adv-btn"; btn.className = "icon-btn";
  btn.title = "Architecture advisor (r)";
  btn.innerHTML = "🧭 <span>Advisor</span>";
  btn.onclick = openAdvisor;
  const bar = q$("#topbar");
  if (bar) bar.insertBefore(btn, q$("#mix-btn") || q$("#theme-btn"));

  document.addEventListener("click", e => { if (e.target.closest(".adv-open")) { e.preventDefault(); openAdvisor(); } });
  addEventListener("keydown", e => {
    if (e.ctrlKey || e.metaKey || e.altKey || e.key !== "r") return;
    if (/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName) || q$("#mix-modal.open")) return;
    if (!isOn()) { openAdvisor(); e.preventDefault(); }
  });
  if (location.hash === "#advisor") setTimeout(openAdvisor, 0);
})();
