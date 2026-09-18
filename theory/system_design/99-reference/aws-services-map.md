# AWS Services Map

Organised by the question they answer, not by AWS's own console categories. The goal is to be able to say "I'd use X because Y" in an interview without hedging.

---

## Messaging & eventing

| Service | It is | Reach for it when |
| --- | --- | --- |
| **SQS** | Managed queue | Decouple two services, absorb bursts, retry work. Standard = at-least-once + best-effort order; FIFO = exactly-once + ordering, 300 msg/s per group |
| **SNS** | Pub/sub topic | Fan out one message to many subscribers (usually SNS → several SQS queues), plus SMS/email/push |
| **EventBridge** | Event bus with content routing | Route by event *content* with JSON rules, not just topic. Schema registry, third-party SaaS sources, archive & replay |
| **EventBridge Scheduler** | Managed cron | Any scheduled invocation. Replaces CloudWatch Events rules and a self-hosted cron box |
| **Kinesis Data Streams** | Partitioned log | Ordered, replayable stream with multiple independent consumers |
| **Amazon Data Firehose** (formerly Kinesis Data Firehose) | Managed delivery | Buffer a stream and land it in S3/Redshift/OpenSearch with no code. The lazy, correct way to archive events |
| **MSK** | Managed Kafka | You need Kafka specifically: many teams on one stream, compacted topics, retention past 365 days, Kafka Connect (via MSK Connect) |
| **IoT Core** | MQTT broker + rules | Devices: per-device certs, device shadow, rules routing to Kinesis/Lambda/DynamoDB |

> **SQS vs SNS vs EventBridge**, the one-liner: SQS is *one consumer pulls work*; SNS is *broadcast to known subscribers*; EventBridge is *route by content to whoever cares*. If asked to pick, EventBridge for integration events between services, SQS for work queues.

## Compute

| Service | Reach for it when |
| --- | --- |
| **Lambda** | Event-driven, bursty, <15 min, scale-to-zero. Watch: cold starts, 10 GB memory cap, 250 MB unzipped package |
| **Fargate (ECS/EKS)** | Containers without managing nodes. Long-running, >15 min, custom runtimes, steady traffic |
| **ECS on EC2 / EKS** | You need node control, GPUs, or the cost curve at scale justifies it |
| **Batch** | Large offline compute jobs with queueing and spot instances |
| **Step Functions** | Orchestrating a *workflow*: retries, branching, parallel, human approval, long waits. Express (high volume, ≤5 min) vs Standard (durable, up to 1 year) |

**Lambda vs Fargate:** Lambda below ~40–50% steady utilisation, Fargate above it. Also Fargate the moment you need a persistent connection pool — Lambda's per-invocation connections will exhaust a Postgres instance unless you put RDS Proxy in front.

## Storage & databases

| Service | Reach for it when |
| --- | --- |
| **S3** | Everything durable and large. Data lake, raw landing zone, backups, static assets. Intelligent-Tiering unless you know your access pattern |
| **DynamoDB** | Predictable key-based access at any scale. On-demand billing removes capacity planning. Streams give free CDC |
| **DAX** | Microsecond reads in front of DynamoDB, write-through, zero app changes |
| **ElastiCache (Valkey/Redis)** | Cache, session store, rate limiting, leaderboards, pub/sub |
| **MemoryDB** | Redis API as a *durable primary* database (multi-AZ transaction log) |
| **RDS / Aurora** | Relational default. Aurora Serverless v2 for spiky workloads; Aurora scales reads to 15 replicas |
| **RDS Proxy** | Lambda + Postgres. Pools connections so 1,000 concurrent invocations don't exhaust the DB |
| **Redshift** | Warehouse when you're committed to AWS-native. Otherwise Snowflake usually wins on ergonomics |
| **Athena** | SQL over S3, pay per TB scanned. Perfect for "query the raw lake occasionally" without a cluster |
| **Glue** | Catalog + Spark ETL. The Data Catalog is the genuinely valuable half — Athena/EMR/Redshift Spectrum all read it |
| **OpenSearch** | Full-text search, log analytics, arbitrary filter combinations |
| **Timestream** | Managed time-series with automatic tiering |
| **Neptune** | Graph |

## API & edge

| Service | Reach for it when |
| --- | --- |
| **API Gateway (REST)** | Full-featured: usage plans, API keys, request validation, WAF. Pricier |
| **API Gateway (HTTP)** | ~70% cheaper, lower latency, fewer features. The default for a plain service API |
| **API Gateway (WebSocket)** | Server→client push: live dashboards, notifications, chat |
| **AppSync** | Managed GraphQL with subscriptions. Strong when the client wants to shape its own queries |
| **ALB** | Containers/EC2 behind a load balancer, path routing |
| **CloudFront** | CDN, TLS termination, edge caching, `CloudFront Functions` for cheap header manipulation |

## Data movement & orchestration

| Service | Reach for it when |
| --- | --- |
| **DMS** | Database migration and ongoing CDC replication into Kinesis/S3/Redshift |
| **MWAA** | Managed Airflow. Batch orchestration with dependencies and backfills |
| **Step Functions** | Event-driven workflow orchestration (vs Airflow's scheduled-batch orientation) |
| **Glue Workflows** | Only if already fully invested in Glue |

**Airflow vs Step Functions:** Airflow for scheduled data pipelines with backfills, sensors and a dependency DAG the data team owns. Step Functions for per-request/per-event workflows that need retries and durable state, defined in IaC next to the services. Many shops run both.

## AI / ML

| Service | Reach for it when |
| --- | --- |
| **Bedrock** | Managed foundation models (incl. Claude) with a single API, guardrails, knowledge bases, VPC privacy |
| **SageMaker** | Train and host your own models |
| **Textract** | Extract text/tables/forms from PDFs and scans — the OCR half of a document pipeline |
| **Comprehend** | Off-the-shelf entity extraction, sentiment, PII detection |
| **Transcribe / Translate / Polly** | Speech-to-text, translation, text-to-speech |

## Observability & security

| Service | Notes |
| --- | --- |
| **CloudWatch** | Metrics, logs, alarms, dashboards. Log Insights for querying |
| **X-Ray** | Distributed tracing across Lambda/API GW/services |
| **Secrets Manager** | Credentials with rotation. Parameter Store is the cheaper option without rotation |
| **KMS** | Encryption keys; envelope encryption for S3/DynamoDB/RDS |
| **IAM** | Roles over keys, always. Least privilege per function |
| **VPC endpoints** | Keep S3/DynamoDB/Kinesis traffic off the public internet — expect this question in any enterprise design |

---

## Reference architectures worth memorising

**Serverless event pipeline**
`API Gateway → Lambda → EventBridge → { Lambda → DynamoDB, Firehose → S3 }`

**Streaming analytics**
`IoT Core → Kinesis Data Streams → Managed Flink → { DynamoDB hot, Firehose → S3 → Athena/Snowflake cold }`

**Document/AI processing**
`S3 upload → EventBridge → Step Functions → { Textract → Bedrock → Aurora } → OpenSearch index`

**CDC to warehouse**
`Aurora → DMS → Kinesis → Firehose → S3 (Iceberg) → Snowflake / Athena`

**Live dashboard**
`Processor → DynamoDB → API Gateway (HTTP) → snapshot` **+** `SNS → API Gateway (WebSocket) → deltas`

---

## Related
- [Streaming tools](streaming-tools.md) · [In-memory databases](in-memory-databases.md) · [SQL vs NoSQL](sql-vs-nosql.md)
