# BorderGate — Border and Passport Control System

This repository contains the implementation and data infrastructure for **BorderGate**, a border-crossing simulation and control system built using Python 3.12+, Redis (Local & Cloud), and Docker Compose.

---

## Prerequisites

- **Python 3.12+**
- **uv** (high-performance Python package and environment manager)
- **Docker Desktop** or **Docker Engine** with Docker Compose

---

## Repository Structure

```text
BorderGate/
├── config/
│   └── redis_clients.py            # Local (Docker) and Cloud Redis client initializers
│   └── cassandra_client.py         # Cassandra session (LOCAL_QUORUM, DC-aware + token-aware routing)
├── cql/
│   ├── schema.cql                  # Keyspace (NetworkTopologyStrategy) and 5 query-driven tables
│   ├── inserts.cql                 # Sample CQL inserts for every table (denormalization example)
│   └── queries.cql                 # CQL queries Q1-Q6 with sample values   
├── data/
│   └── seed_data/                  # Initial synthetic dataset CSV files
│       ├── cassandra_border_crossings.csv
│       ├── cloud_agent_sessions.csv
│       ├── cloud_stolen_passports.csv
│       ├── cloud_visa_policies.csv
│       ├── cloud_wanted_persons.csv
│       └── docker_passenger_queue.csv
├── docker/
│   ├── docker_compose.yml          # Local Redis cluster & Sentinel topology
│   ├── sentinel.conf.example       # Static base template for Sentinel configuration
│   ├── sentinel1.conf              # Node 1 local config (Git ignored)
│   ├── sentinel2.conf              # Node 2 local config (Git ignored)
│   └── sentinel3.conf              # Node 3 local config (Git ignored)
├── src/
│   ├── consumer.py                 # Booth worker process
│   ├── evaluator.py                # Security rules evaluation engine
│   ├── secondary_review.py         # Priority-ranked second-line inspection monitor
│   ├── security_alerts.py          # Real-time Pub/Sub security breach listener
│   ├── seed_redis.py               # Redis Cloud & Local data loader
│   ├── seed_cassandra.py           # Cassandra loader (denormalized writes to 5 tables)
│   ├── query_cassandra.py          # Cassandra queries Q1-Q6 with execution time (ms)
│   └── test_connect.py             # Connection validation script
├── .env                            # Local credentials & ports (Git ignored)
├── .env.example                    # Environment template without credentials
├── .gitignore                      # Git exclusion rules (.env, .venv, sentinel*.conf)
├── pyproject.toml                  # Dependency management (uv)
├── README.md                       # Project documentation
└── uv.lock                         # Lockfile managed by uv
```

---

## Getting Started

### 1. Install Dependencies

Sync and set up the virtual environment using `uv`:

```bash
uv sync
```

---

### 2. Environment Variables (`.env`)

Ensure a `.env` file exists at the project root with the following variables (you can copy `.env.example` as a template):

```env
# Local Instance (Docker)
REDIS_LOCAL_HOST=localhost

# Local port exposed by Docker Compose (Default: 6379)
REDIS_LOCAL_PORT=6379

# Cloud Instance (Redis Enterprise)
REDIS_CLOUD_HOST=your-redis-cloud-endpoint.db.redis.io
REDIS_CLOUD_PORT=12438
REDIS_CLOUD_USER=default
REDIS_CLOUD_PASSWORD=your_password

# Cassandra (Docker, single node)
CASSANDRA_HOST=localhost
CASSANDRA_PORT=9042
CASSANDRA_KEYSPACE=border_crossing
CASSANDRA_LOCAL_DC=Mad_Barajas
```

---

### 3. Generate Sentinel Configuration Files

Redis Sentinel rewrites its configuration on disk whenever node roles change, so each Sentinel needs its own copy of the template. Create the 3 files before launching Docker Compose:

```bash
cp docker/sentinel.conf.example docker/sentinel1.conf
cp docker/sentinel.conf.example docker/sentinel2.conf
cp docker/sentinel.conf.example docker/sentinel3.conf
```

---

### 4. Start the Local Cluster (Docker)
The local infrastructure consists of a high-availability Redis cluster and an Apache Cassandra node defined in `docker/docker_compose.yml`, composed of:

- **1 Primary Master node** (`redis-local` / `bordergate-redis-local`, default port `6379`) with AOF persistence (`redis_local_data`).
- **2 Replicas** (`redis-replica-1` on port `6380`, `redis-replica-2` on port `6381`).
- **3 Sentinel instances** (`sentinel-1`, `sentinel-2`, `sentinel-3` on port `26379`) on `redisnet`, providing distributed consensus with a quorum of 2 (`2/3`). Every Sentinel monitors all 3 Redis nodes.
- **1 Apache Cassandra 5.0 node** (`cassandra` / `bordergate-cassandra`, CQL native port `9042`) on `bordergate-net`, configured as the historical archive (`Cluster: BorderGate`, `DC: Mad_Barajas`, `Rack: rack1`, `16 vnodes`, `512M` JVM heap) with persistent storage (`bordergate-cassandra-data`).

```text
    ╔═════════════════════╗            ╔═════════════════════╗            ╔═════════════════════╗
    ║     sentinel-1      ║◄══════════►║     sentinel-2      ║◄══════════►║     sentinel-3      ║
    ║    (Port: 26379)    ║            ║    (Port: 26379)    ║            ║    (Port: 26379)    ║
    ╚══════════╤══════════╝            ╚══════════╤══════════╝            ╚══════════╤══════════╝
               │                                  │                                  │
    ┌──────────┴──────────────────────────────────┴──────────────────────────────────┴──────────┐
    │                    Every Sentinel monitors ALL 3 Redis nodes (PING: 5s)                    │
    │                    + Auto-Failover Orchestration · Quorum 2/3 · Pub/Sub                    │
    └──────────┬──────────────────────────────────┬──────────────────────────────────┬──────────┘
               │                                  │                                  │
               ▼                                  ▼                                  ▼
╔════════════════════════════╗     ╔════════════════════════════╗     ╔════════════════════════════╗
║ bordergate-redis-replica-1 ║     ║   bordergate-redis-local   ║     ║ bordergate-redis-replica-2 ║
║     [REPLICA 1 : 6380]     ║◄════║  [PRIMARY MASTER : 6379]   ║════►║     [REPLICA 2 : 6381]     ║
║    (Read-Only · slave)     ║     ║    (Read / Write · AOF)    ║     ║    (Read-Only · slave)     ║
╚════════════════════════════╝     ╚════════════════════════════╝     ╚════════════════════════════╝
```
CASSANDRA
```text
────────────────────────────────────────
  APACHE CASSANDRA (Docker, 1 node)
   Keyspace: border_crossing
   DC: Mad_Barajas · RF = 1
   Consistency: LOCAL_QUORUM
   • 5 query-driven tables
   • Q1–Q6 single-partition reads
```


Launch the cluster:

```bash
docker compose -f docker/docker_compose.yml up -d
```

---
### 5. Verify the Cluster

Check that all 7 containers (`bordergate-redis-local`, `bordergate-redis-replica-1`, `bordergate-redis-replica-2`, `bordergate-sentinel-1`, `bordergate-sentinel-2`, `bordergate-sentinel-3`, and `bordergate-cassandra`) report status `Up`:

```bash
docker compose -f docker/docker_compose.yml ps
```
Check that the master responds:

```bash
docker exec -it bordergate-redis-local redis-cli PING
# Expected output: PONG
```

Check that Sentinel sees the full topology:

```bash
docker exec bordergate-sentinel-1 redis-cli -p 26379 sentinel master bordergate-master | paste - - | column -t
```

*Expected values:* `flags: "master"`, `ip: "redis-local"`, `num-slaves: "2"`, `num-other-sentinels: "2"`, `quorum: "2"`.

Check that the Apache Cassandra node is Up/Normal (`UN`) in datacenter `Mad_Barajas` (allow ~30–45 seconds after startup for JVM initialization):

```bash
docker exec bordergate-cassandra nodetool status
```
*Expected output:* `Datacenter: Mad_Barajas` with node status `UN` (`Up` / `Normal`) and `16` tokens.

Load the schema
```bash
docker exec -i bordergate-cassandra cqlsh < cql/schema.cql
```
---

### 6. Test Connections

Run the connectivity test script to verify communication with both Redis (Local & Cloud) and Cassandra instances:

```bash
uv run python -m src.test_connect
```

---

### 7. Seed the Database

Upload  control data (stolen passports, wanted individuals, visa policies, active officer sessions) to Redis Cloud and load initial passenger queues in the local Redis master. The two replicas receive the local data automatically through replication.

```bash
uv run python -m src.redis.seed_redis
```

We can also select wich database we want to seed:
```bash
uv run python -m src.redis.seed_redis --local
uv run python -m src.redis.seed_redis --cloud

```
Allows rapid local queue resets during testing without re-uploading global cloud datasets. 

WARNING
--------------------------------------------------------------------------------
Processing passengers consumes and clears the local booth queues. To re-run the 
simulation or execute consecutive test batches, you MUST re-seed the local Redis 
instance using the `--local` flag:
```bash
  uv run python -m src.seed_redis --local
```

---

## Execution & Monitoring Workflow

### Step 1: Launch Real-Time Security Alerts Monitor

Start the security breach subscriber to catch high-priority arrest alerts broadcasted from any booth via Pub/Sub:

```bash
uv run python -m src.redis.security_alerts
```

---
### Step 2: Run Booth Workers

Start processing passengers at individual border control booths. You can pass 
BOOTH_ID as a CLI argument or environment variable:

1. Running a single booth worker
```bash
# Via argument (BOX-001 to BOX-012)
uv run python -m src.redis.consumer BOX-001

# Or via environment variable (e.g., BOX-002)
BOOTH_ID=BOX-002 uv run python -m src.redis.consumer
```
2. Spawn all 12 booths at the same time

To spawn workers for all 12 booths at the same time in background processes:
```bash
for i in $(seq -f "%03g" 1 12); do BOOTH_ID="BOX-$i" uv run python -m src.redis.consumer & done
```
**Concurrency output & interference note**:

Executing the 12 processes simultaneously in background causes 
broken visual formatting in the terminal.

Because all 12 independent Python processes write concurrently to the same 
standard output stream (stdout) without I/O locking, prints, security 
alerts, and completion summaries coincide in time and unpredictably appear
on screen without a logical order.
---

### Step 3: Run Secondary Inspection Review Desk

Start the second-line inspection workspace. Launching this monitor after or during booth processing allows it to consume flagged passengers from the priority-sorted queue (`ZSET`), processing candidates by highest cumulative risk score rather than order of arrival:

```bash
uv run python -m src.redis.secondary_review
```

---

## Architecture Overview after seeding

```text
                  ┌─────────────────────────────────────────────────────────┐
                  │               BORDERGATE HYBRID ARCHITECTURE            │
                  └────────────────────────────┬────────────────────────────┘
                                               │
               ┌───────────────────────────────┴───────────────────────────────┐

          REDIS CLOUD                                                  REDIS LOCAL / DOCKER
  ───────────────────────────────                                ────────────────────────────────────
- Stolen Passports Blacklist                                   • Live Passenger Ingestion Queues
    ├─ SET  : blacklist:stolen_passports                            └─ LIST : queue:passengers:<booth_id> (FIFO via RPUSH/BLMOVE)
    └─ HASH : stolen:<passport_number>                           • Work-in-Progress Queues
- Wanted Persons & Threat Ranking                                 └─ LIST : queue:passengers:processing:<booth_id>
    ├─ ZSET : blacklist:wanted_persons (Score: 1-4)              • Priority-Ranked Secondary Inspection
    └─ HASH : wanted:<passport_number>                              └─ ZSET : queue:secondary_review:ranking (Pop via ZPOPMAX)
- Country Visa Entry Policies                                  • Local Audit Trail & Event Persistence
    └─ HASH : policy:visa:<country_code>                            └─ HASH : log:<YYYY-MM-DD>:<ticket_number> (7-Day TTL)
- Active Officer Sessions & Mapping
    ├─ HASH : session:agent:<badge_number> (With TTL)
    └─ STRING: cabin:active:<booth_id> -> badge_number
- Real-Time Security Breach Alerts
    └─ Pub/Sub: alerts:security_breach
```
---

## Replication & High Availability Tests

Run these simulations once the cluster is up and the booth workers have processed some passengers (see [Execution & Monitoring Workflow](#execution--monitoring-workflow)).

### 1. Verify Asynchronous Replication

In order to check that the master and both replicas hold the same data,  we can compare the logs that each replica has, as they are not deleted in the evualation/monitoring process as other data:


Audit logs are stored as log:<YYYY-MM-DD>:<ticket_number>, so the exact key name is not known in advance. The first command picks one existing log key from the master and stores it in KEY, so the same key can then be queried on all three nodes.
```bash
# Master
KEY=$(sudo docker exec bordergate-redis-local redis-cli --scan --pattern "log:*" | head -n 1)

sudo docker exec bordergate-redis-local redis-cli HGETALL "$KEY" | paste - - | column -t
```
```bash
# Replica 1 (Port 6380)
sudo docker exec bordergate-redis-replica-1 redis-cli HGETALL "$KEY" | paste - - | column -t
```

```bash
# Replica 2 (Port 6381)
sudo docker exec bordergate-redis-replica-2 redis-cli HGETALL "$KEY" | paste - - | column -t
```

*Expected Result:* Both replicas return the identical log as the master.

---

### 2. Verify Read-Only Enforcement on Replicas

Client writes directly targeting a replica must be rejected:

```bash
docker exec -it bordergate-redis-replica-1 redis-cli SET test_bypass "unauthorized"
```

*Expected Output:*

```text
(error) READONLY You can't write against a read only replica.
```

---

### 3. Automatic Failover

Simulate an unexpected crash of the primary master node to observe Sentinel's automatic leader election and failover.

1. **Stream Sentinel events in real time (Terminal 1):**

   ```bash
   docker logs -f bordergate-sentinel-1
   ```

2. **Simulate primary node crash (Terminal 2):**

   ```bash
   docker stop bordergate-redis-local
   ```

3. **Verify automated election in Sentinel logs:**

   - `+sdown master bordergate-master ...` (Subjective down detected after 5000ms)
   - `+odown master bordergate-master ... #quorum 2/2` (Objective down confirmed by quorum)
   - `+try-failover` and `+vote-for-leader` (Sentinel quorum elects leader)
   - `+failover-end` and `+switch-master` (A replica is promoted to the new master)

4. **Query active master endpoint:**

   ```bash
   docker exec -it bordergate-sentinel-1 redis-cli -p 26379 sentinel get-master-addr-by-name bordergate-master
   ```

   *Expected Result:* Returns the internal IP and port `6379` of the promoted replica (e.g., `172.22.0.4`).

5. **Restart old master and verify auto-reconfiguration:**

   ```bash
   docker start bordergate-redis-local
   ```

   In the Sentinel logs, verify that the revived node is re-integrated cleanly without conflicts:

   - `-sdown slave redis-local:6379 ...` (Node marks available)
   - `+slave slave 172.22.0.2:6379 ...` (Reconfigured as replica under the new master)

   Verify role degradation directly:

   ```bash
   docker exec -it bordergate-redis-local redis-cli INFO replication
   ```

   *Confirmed Parameters:* `role:slave`, `master_link_status:up`, `slave_read_only:1`.

---

### 4. Fully Manual Failover

To perform a complete manual role switch without Sentinel intervention:

1. **Stop all Sentinel instances:**

   ```bash
   docker stop bordergate-sentinel-1 bordergate-sentinel-2 bordergate-sentinel-3
   ```

2. **Promote a designated replica to Master:**

   ```bash
   docker exec -it bordergate-redis-replica-1 redis-cli REPLICAOF NO ONE
   ```

   Verify role promotion:

   ```bash
   docker exec -it bordergate-redis-replica-1 redis-cli INFO replication | grep role
   # Expected output: role:master
   ```

3. **Re-point the second replica to the new Master:**

   ```bash
   docker exec -it bordergate-redis-replica-2 redis-cli REPLICAOF redis-replica-1 6379
   ```

4. **Demote the old master to replica:**

   ```bash
   docker exec -it bordergate-redis-local redis-cli REPLICAOF redis-replica-1 6379
   ```

   Verify demoted role:

   ```bash
   docker exec -it bordergate-redis-local redis-cli INFO replication | grep role
   # Expected output: role:slave
   ```
---
### 5. Reset Topology to Baseline State

To return the deployment to its initial architecture where `bordergate-redis-local` acts as the primary master we could do it manually as previously shown or by just restarting the docker container:

```bash
docker compose -f docker/docker_compose.yml down
docker compose -f docker/docker_compose.yml up -d
```

Confirm that the original master has regained its primary role:

```bash
docker exec -it bordergate-redis-local redis-cli INFO replication | grep role
# Expected output: role:master

docker exec -it bordergate-sentinel-1 redis-cli -p 26379 sentinel get-master-addr-by-name bordergate-master
# Expected output: points back to redis-local 
```

---

## Cassandra — Historical Border Crossing Archive

Redis keeps the **live** state of the border (queues, sessions, alerts) and its audit logs expire after 7 days (`log:<date>:<ticket>`, TTL 604800 s). Cassandra is the **permanent historical archive**: every crossing is stored (synthetical) and can be queried by passport, booth/day, alerts, secondary inspections and daily statistics.


### 1. Create the Schema

```bash
docker exec -i bordergate-cassandra cqlsh < cql/schema.cql
```

> Use `-i` (not `-it`) when redirecting a file into `cqlsh`.

Verify:

```bash
docker exec -it bordergate-cassandra cqlsh -k border_crossing -e "DESCRIBE TABLES;"
docker exec -it bordergate-cassandra cqlsh -e "SELECT keyspace_name, durable_writes, replication FROM system_schema.keyspaces WHERE keyspace_name = 'border_crossing';"
```

*Expected:* 5 tables in `border_crossing`, `durable_writes = True`, `NetworkTopologyStrategy` with `Mad_Barajas: 1`.

---

### 2. Load the Dataset

`data/seed_data/cassandra_border_crossings.csv` contains 5,147 synthetic crossings (12 Oct – 10 Nov 2026) built from similar data used by Redis (booths, officers, stolen/wanted passports, visa policies). Each crossing is written to every table that needs it:

            cassandra_border_crossings.csv  (1 row = 1 crossing)
                                │
                                ▼
                   src/seed_cassandra.py (prepared statements)
                                │
      ┌─────────────────┬───────┴──────────┬──────────────────┬───────────────────────┐
      │ always          │ always           │ always (+1)      │ if DENIED_*           │ if SECONDARY_INSPECTION
      ▼                 ▼                  ▼                  ▼                       ▼
crossings_by_      crossings_by_      crossing_stats_     alerts_by_day      secondary_reviews_by_day
  passport           booth_day           by_day               (Q4)                   (Q5)
   (Q1)              (Q2, Q3)          (Q6, counter)

```bash
uv run python -m src.cassandra.seed_cassandra
```

*Expected Output:*

```text
  by_passport: 5147 writes
  by_booth_day: 5147 writes
  alerts: 287 writes
  secondary: 338 writes
  stats: 5147 writes
Done in 'x' s
```

Load design:
- **Prepared statements** (parsed once, typed, token-aware routing).
- **Empty optional fields are sent as `UNSET_VALUE`**, never `null`, to avoid creating tombstones.
- **No `BATCH`**: multi-partition batches are an anti-pattern for bulk loading in Cassandra.
- **Counters are not idempotent**, so `crossing_stats_by_day` is truncated before every load. The other tables are safe to reload (same `crossing_id` → upsert).

Optional — sample CQL inserts (run once; the counter `UPDATE` is not idempotent):

```bash
docker exec -i bordergate-cassandra cqlsh < cql/inserts.cql
```

---

### 3. Run the Queries

CQL version (sample values):

```bash
docker exec -i bordergate-cassandra cqlsh < cql/queries.cql
```

Python version with execution times (each query runs 5 times; average and minimum in ms):

```bash
uv run python -m src.cassandra.query_cassandra
```

*Expected Output (times vary per machine):*

```text
Q     Rows   Avg (ms)   Min (ms)   Description
Q1      43       1.51       0.92   Crossing history of a passport (most recent first).
Q2       9       0.87       0.64   All crossings at a booth on a given day (chronological order).
Q3       6       1.25       0.88   Crossings at a booth on a given day within a time range.
Q4       9       0.89       0.73   Security alerts raised at booths on a given day (most recent first).
Q5       5       1.32       0.81   Top-N most urgent secondary inspections on a given day.
Q6      54       1.74       1.20   Number of crossings by status and nationality on a given day.
```

Every query reads a **single partition**, located directly from the hash of its partition key: no joins, no full scans, no sorting at query time.

---

### Data Model (Query-Driven, Chebotko)

| Table | Queries | Partition Key | Clustering Key | Notes |
|---|---|---|---|---|
| `crossings_by_passport` | Q1 | `passport_number` | `crossing_ts DESC`, `crossing_id ASC` | `full_name`, `nationality` are `STATIC` |
| `crossings_by_booth_day` | Q2, Q3 | (`booth_id`, `crossing_date`) | `crossing_ts ASC`, `crossing_id ASC` | Daily bucketing bounds partition size |
| `alerts_by_day` | Q4 | `crossing_date` | `crossing_ts DESC`, `crossing_id ASC` | Only `DENIED_*` crossings |
| `secondary_reviews_by_day` | Q5 | `crossing_date` | `secondary_priority DESC`, `crossing_ts ASC`, `crossing_id ASC` | Top-N with `LIMIT` |
| `crossing_stats_by_day` | Q6 | `crossing_date` | `status ASC`, `nationality ASC` | `crossing_count` counter |

| ID | Query |
|---|---|
| Q1 | Crossing history of a passport (most recent first) |
| Q2 | All crossings at a booth on a given day (chronological order) |
| Q3 | Crossings at a booth on a given day within a time range |
| Q4 | Security alerts raised at booths on a given day (most recent first) |
| Q5 | Top-N most urgent secondary inspections on a given day |
| Q6 | Number of crossings by status and nationality on a given day |

`crossing_id` (UUID) is shared by all tables, so the same crossing can be traced across the denormalized copies.

---

### Replication & Consistency

| Setting | Value | Reason |
|---|---|---|
| Replication strategy | `NetworkTopologyStrategy` | Consistent with the configured topology, production-recommended, allows adding datacenters with `ALTER KEYSPACE` |
| Replication factor | `Mad_Barajas: 1` | Single node: more replicas than nodes is not possible. No fault tolerance (accepted lab limitation) |
| Consistency level | `LOCAL_QUORUM` (client side) | With RF=1 it equals 1 replica (R + W = 2 > RF). If RF grows to 3 it becomes 2 + 2 > 3 with no code changes, and never waits for remote datacenters |

The consistency level is set per session in `config/cassandra_client.py`, not in the keyspace: Cassandra uses tunable consistency per operation.

---

### Stop / Start the Node

```bash
docker stop bordergate-cassandra
docker start bordergate-cassandra   # wait for "Starting listening for CQL clients"
```

Data persists in the `bordergate-cassandra-data` volume.

---

## Cassandra Tests

### 1. Partition Strategy Evidence

```bash
docker exec -it bordergate-cassandra nodetool flush
docker exec -it bordergate-cassandra nodetool tablestats border_crossing
```

*Check:* `Number of partitions (estimate)` per table. `crossings_by_booth_day` holds one small partition per booth and day (daily bucketing), while `alerts_by_day` and `secondary_reviews_by_day` hold one partition per day.

Locate the node that owns a partition (partition key → Murmur3 token → node):

```bash
docker exec -it bordergate-cassandra nodetool getendpoints border_crossing crossings_by_passport ESP-572524
docker exec -it bordergate-cassandra nodetool getendpoints border_crossing crossings_by_booth_day BOX-007:2026-10-21
```

---

### 2. Quorum Requirement (RF > available replicas)

```sql
CREATE KEYSPACE quorum_test WITH replication = {'class': 'NetworkTopologyStrategy', 'Mad_Barajas': 3};
CREATE TABLE quorum_test.t (id int PRIMARY KEY, v text);

CONSISTENCY LOCAL_QUORUM;
INSERT INTO quorum_test.t (id, v) VALUES (1, 'test');   -- fails: 2 replicas required, 1 alive

CONSISTENCY ONE;
INSERT INTO quorum_test.t (id, v) VALUES (1, 'test');   -- succeeds

DROP KEYSPACE quorum_test;
```

*Expected Result:* with RF = 3 on a single node, `LOCAL_QUORUM` (2 replicas) cannot be achieved; `ONE` succeeds. This is why `border_crossing` uses `Mad_Barajas: 1`.

---

### 3. Node Failure Handling

```bash
docker stop bordergate-cassandra
uv run python -m src.cassandra.query_cassandra
```

*Expected Output:*

```text
ConnectionError: Could not connect to Cassandra at localhost:9042
```

```bash
docker start bordergate-cassandra
```

Once the node accepts CQL connections again, all data is still available (persistent volume).

---

### 4. Query-Driven Model: Non-Key Filtering Is Rejected

```sql
SELECT crossing_ts, full_name, status FROM border_crossing.alerts_by_day WHERE nationality = 'NGA';
```

*Expected Result:* `InvalidRequest ... use ALLOW FILTERING`. Filtering by a non-key column would scan every partition; the correct solution in Cassandra is a new table designed for that query, not `ALLOW FILTERING`.