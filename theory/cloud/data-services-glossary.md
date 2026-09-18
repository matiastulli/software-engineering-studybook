# Data Services Glossary — AWS and the Tools Around It

A short "what is this, where does it fit, where's the official page" card for data services that come up in interviews and job descriptions. Everything here runs on AWS: first the AWS services, then the third-party tools you commonly plug into an AWS stack. For when to pick which, see [architecture-comparison.md](architecture-comparison.md), whose §12 shows each service inside the six cases.

## TL;DR

- "DynamoDB is AWS's key-value database: millisecond reads by key at any scale, as long as I design the table around the lookups I need."
- "Firehose delivers a stream into S3, Snowflake or Redshift. It's a pipe, not a log, so if anything needs to re-read events I put Kinesis Data Streams in front."
- "Flink on AWS is Managed Service for Apache Flink; Kafka on AWS is MSK, and Kafka Connect runs on MSK Connect."
- "Devices that speak MQTT connect to IoT Core, which routes their messages into Kinesis or Lambda."
- "Fivetran and Airbyte copy SaaS and database tables into the warehouse. Fivetran is paid and fully managed; Airbyte is open source and can run inside my own VPC."

---

## The problem

Every stack renames the same handful of jobs, and vendors add their own products on top. In an interview, "we use Firehose into S3 and Flink on the hot path" only makes sense if you can map each name to its **job** (ingest, transport, process, store, analyze) in a second. The tables below do that mapping.

---

## AWS services

| Service | Job | What it is |
|---|---|---|
| [**DynamoDB**](https://aws.amazon.com/dynamodb/) | Operational store | A fully managed key-value / wide-column NoSQL database. You pick a partition key (and optional sort key), and reads by key take single-digit milliseconds at any scale. No joins, and queries must follow the key design, so you model tables around your access patterns. Conditional writes ("only if newer") make consumers idempotent; Streams give you a 24-hour change feed. |
| [**Amazon Data Firehose**](https://aws.amazon.com/firehose/) (formerly *Kinesis Data Firehose*) | Delivery (stream → storage) | A managed "pipe into a destination". It takes records, buffers them for a size or time window (0–900 s), optionally converts them (e.g. JSON → Parquet), and writes batches to S3, Redshift, Snowflake, OpenSearch or an HTTP endpoint. It is not a log: consumers can't re-read or replay it. |
| [**Managed Service for Apache Flink**](https://aws.amazon.com/managed-service-apache-flink/) | Stream processing | AWS's hosted [Apache Flink](https://flink.apache.org/) (formerly *Kinesis Data Analytics*). Flink keeps **state per key** (e.g. "last ping of truck 42"), handles late data with event time and watermarks, fires timers ("truck silent for 10 minutes"), and restores exactly-once state from checkpoints in S3. |
| [**Amazon MSK**](https://aws.amazon.com/msk/) | Transport (log) | Apache Kafka run by AWS, as provisioned brokers or MSK Serverless. The pick over Kinesis when many teams share the same events, you need compacted topics, or retention past 365 days. |
| [**MSK Connect**](https://docs.aws.amazon.com/msk/latest/developerguide/msk-connect.html) (Kafka Connect) | Delivery in and out of Kafka | Runs [Kafka Connect](https://kafka.apache.org/documentation/#connect) connectors without your own workers. A **source** connector pulls into Kafka (e.g. Debezium CDC from Postgres); a **sink** connector reads a topic and writes it to S3, Snowflake or OpenSearch. A sink connector is the Kafka equivalent of Firehose. |
| [**AWS IoT Core**](https://aws.amazon.com/iot-core/) | Device ingestion | AWS's managed [MQTT](https://mqtt.org/) broker. MQTT is a lightweight publish/subscribe protocol built for devices on flaky, low-bandwidth networks: trucks publish to topics like `trucks/42/gps` over one persistent connection. IoT Core gives each device its own certificate, and its rules engine forwards messages into Kinesis, Lambda or DynamoDB. |
| [**Amazon Redshift**](https://aws.amazon.com/redshift/) | Analytics warehouse | AWS's own SQL data warehouse. **Is it like Snowflake? Yes**, both are columnar SQL warehouses for scanning billions of rows. Redshift keeps everything on one AWS bill and has a serverless option; Snowflake needs less tuning (no distribution or sort keys to design), gives each team its own compute, and has the bigger dbt ecosystem. Both load straight from S3. |

---

## Third-party tools on AWS

| Tool | Job | What it is |
|---|---|---|
| [**Fivetran**](https://www.fivetran.com/) | Ingestion (ELT) | A paid, fully managed connector service. You pick a source (Salesforce, HubSpot, Postgres, Stripe…) and a destination (Snowflake, Redshift, S3) and it keeps the tables in sync, handling schema changes and incremental loads. Priced by monthly active rows. |
| [**Airbyte**](https://airbyte.com/) | Ingestion (ELT) | The open-source alternative to Fivetran: hundreds of connectors you can self-host for free (on EC2 or EKS inside your VPC), or use as Airbyte Cloud. Cheaper and customizable, at the cost of operating it yourself. |
| [**Confluent Cloud**](https://www.confluent.io/confluent-cloud/) | Transport (log) | Fully managed Kafka sold by Confluent, the company founded by Kafka's creators. It can run in your AWS region and bundles managed connectors, Schema Registry and Flink. The AWS-native choice for the same job is MSK. |
| [**Snowflake**](https://www.snowflake.com/) | Analytics warehouse | The default warehouse in this repo. You create the account in the same AWS region as your S3 buckets, and Snowpipe loads new S3 files within about a minute. |

---

## Decide

- **Copy SaaS/database tables into the warehouse:** pick Fivetran when the team is small and time is worth more than money; switch to Airbyte when connector costs grow, you need a custom source, or data must stay inside your VPC. Switch to DMS (CDC) when you need changes within minutes, including deletes.
- **Kafka on AWS:** MSK by default; Confluent Cloud if you want Schema Registry, connectors and Flink bundled and managed by one vendor.
- **Stream into storage:** Firehose when the stream is Kinesis; an S3 sink on MSK Connect when the stream is Kafka.
- **Stateful stream processing:** Lambda until you need per-key state or timers, then Managed Flink.
- **Warehouse:** Snowflake by default; Redshift when the company wants everything AWS-native.
- **Devices on cellular networks:** IoT Core (MQTT) in front of Kinesis when you own the devices; API Gateway when a tracking vendor sends webhooks.

## Failure modes

- **Treating Firehose as a log.** It delivers and forgets; if a second consumer needs the data or you need replay, put Kinesis Data Streams or MSK in front.
- **Designing DynamoDB like Postgres.** Tables without a plan for access patterns end in full scans and hot partitions.
- **Relying on DynamoDB Streams for recovery.** They keep 24 hours. A consumer outage over a weekend loses changes unless you alarm early.
- **Self-hosting Airbyte or Kafka Connect "because it's free"** and then owning upgrades, scaling and failed-sync alerts.

---

## Self-check

<details><summary><b>Q1.</b> Which AWS service does each job: Kafka, Flink, Kafka Connect, an MQTT broker?</summary>

Kafka → **Amazon MSK**. Flink → **Managed Service for Apache Flink**. Kafka Connect → **MSK Connect**. MQTT broker → **AWS IoT Core**.

</details>

<details><summary><b>Q2.</b> Is Redshift like Snowflake? When would you pick each?</summary>

Yes, both are columnar SQL warehouses that load from S3. Snowflake by default: less tuning, separate compute per team, bigger dbt ecosystem. Redshift when the company wants everything AWS-native on one bill.

</details>

<details><summary><b>Q3.</b> What's the difference between Firehose and a Kafka Connect sink, and what do they have in common?</summary>

Same job: take a stream and write it into storage (S3, Snowflake…) without custom consumer code. Firehose is an AWS service fed by Kinesis or direct puts; a Kafka Connect sink is a connector (on MSK Connect) that reads from a Kafka topic.

</details>

<details><summary><b>Q4.</b> Fivetran vs Airbyte: when would you pick each?</summary>

Fivetran when you want zero operations and can pay per active row. Airbyte when cost matters, you need a custom connector, or data must stay inside your VPC; the price is running it yourself (or paying for Airbyte Cloud).

</details>

<details><summary><b>Q5.</b> Where does IoT Core sit in a truck-telemetry pipeline, and why MQTT instead of HTTP?</summary>

At the very edge: trucks publish to IoT Core, whose rules forward messages into Kinesis. MQTT keeps one lightweight persistent connection, tolerates flaky cellular links and has delivery-level QoS, which is cheaper and more reliable than an HTTP request per ping. Each truck also gets its own certificate, so a stolen key affects one truck.

</details>

<details><summary><b>Q6.</b> When does DynamoDB fit better than Aurora PostgreSQL?</summary>

When every read is a lookup by a known key (latest position of truck 42, a connection ID) at high volume and you don't need joins or ad-hoc queries. Aurora stays the source of truth for orders, billing and anything relational.

</details>
