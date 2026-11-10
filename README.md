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

├── data/

│   └── seed_data/                  # Initial synthetic dataset CSV files

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

│   ├── consumer.py                 # E-Gate booth worker process

│   ├── evaluator.py                # Security rules evaluation engine

│   ├── secondary_review.py         # Priority-ranked second-line inspection monitor

│   ├── security_alerts.py          # Real-time Pub/Sub security breach listener

│   ├── seed_redis.py               # Redis Cloud & Local data loader

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

```



---



### 3. Start Local Redis (Docker)



Launch the local Redis container using Docker Compose:



```bash

docker compose -f docker/docker_compose.yml up -d

```



To verify that the container is up and responding:



```bash

docker exec -it bordergate-redis-local redis-cli PING

# Expected output: PONG

```



---



### 4. Test Connections



Run the connectivity test script to verify communication with both Local and Cloud Redis instances:



```bash

uv run python -m src.test_connect

```



---



### 5. Seed the Database



Upload global control data (stolen passports, wanted individuals, visa policies, active officer sessions) to Redis Cloud and populate initial passenger queues in local Redis:



```bash

uv run python -m src.seed_redis

```



---



## Execution & Monitoring Workflow



### Step 1: Launch Real-Time Security Alerts Monitor



Start the security breach subscriber to catch high-priority arrest alerts broadcasted from any booth via Pub/Sub:



```bash

uv run python -m src.security_alerts

```



---



### Step 2: Run E-Gate Booth Workers



Start processing passengers at individual border control booths. You can pass `BOOTH_ID` as a CLI argument or environment variable:



```bash

# Run a single booth worker (e.g., BOX-001)

uv run python -m src.consumer BOX-001



# Or via environment variable

BOOTH_ID=BOX-002 uv run python -m src.consumer

```



To spawn workers for all 12 available booths sequentially:



```bash

for i in $(seq -f "%03g" 1 12); do BOOTH_ID="BOX-$i" uv run python -m src.consumer & done

```



---



### Step 3: Run Secondary Inspection Review Desk



Start the second-line inspection workspace. Launching this monitor after or during booth processing allows it to consume flagged passengers from the priority-sorted queue (`ZSET`), processing candidates by highest cumulative risk score rather than order of arrival:



```bash

uv run python -m src.secondary_review

```



---



## Architecture Overview



BorderGate relies on a hybrid data topology to maximize throughput, enforce strict data sovereignty/privacy constraints, and remain within Redis Cloud free-tier memory allocations:



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



### Key & Data Structure Specifications


| Scope | Key Pattern | Type | Operations | Purpose / Description |
|---|---|---|---|---|
| **Cloud** | `blacklist:stolen_passports` | `SET` | `SISMEMBER`, `SADD` | Global lookup for stolen passport numbers. |
| **Cloud** | `stolen:<passport_number>` | `HASH` | `HGETALL`, `HSET` | Complete incident report details for stolen passports. |
| **Cloud** | `blacklist:wanted_persons` | `ZSET` | `ZSCORE`, `ZADD` | Fugitive blacklist sorted by threat score (`1` Low to `4` Critical). |
| **Cloud** | `wanted:<passport_number>` | `HASH` | `HGETALL`, `HSET` | Active arrest warrant details and alert instructions. |
| **Cloud** | `policy:visa:<country_code>` | `HASH` | `HGETALL`, `HSET` | Country-specific visa entry rules (`visa_required: True/False`). |
| **Cloud** | `session:agent:<badge_number>` | `HASH` | `HGETALL`, `EXPIRE` | Active police officer credentials and session metrics. |
| **Cloud** | `cabin:active:<booth_id>` | `STRING` | `GET`, `SET` | Maps booth ID to officer badge number. |
| **Cloud** | `alerts:security_breach` | `Pub/Sub` | `PUBLISH`, `SUBSCRIBE` | Real-time alert broadcast channel for high-level breaches (SUB). |
| **Local** | `queue:passengers:<booth_id>` | `LIST` | `RPUSH`, `BLMOVE` | Per-booth incoming passenger buffer (FIFO queue). |
| **Local** | `queue:passengers:processing:<booth_id>` | `LIST` | `BLMOVE`, `LREM` | Atomic in-flight processing list for resilience against crashes. |
| **Local** | `queue:secondary_review:ranking` | `ZSET` | `ZADD`, `ZPOPMAX` | Priority queue ordered by dynamic risk score (`(50 if not nfc_valid) + (100 - bio_score * 100)`). |
| **Local** | `log:<YYYY-MM-DD>:<ticket_number>` | `HASH` | `HSET`, `EXPIRE` | Audit trail per passenger check with a 7-day TTL expiration. |


---



## High Availability, Replication & Sentinel Topology



To ensure zero downtime, data resilience, and seamless fault tolerance at border checkpoints, the local infrastructure uses a high-availability Redis cluster composed of:

- **1 Primary Master node** (`redis-local`, default port `6379`)

- **2 Replicas** (`redis-replica-1` on port `6380`, `redis-replica-2` on port `6381`)

- **3 Sentinel instances** (`sentinel-1`, `sentinel-2`, `sentinel-3` on port `26379`), providing distributed consensus with a quorum of 2 (`2/3`).

This is defined in the docker_compose.yml.

```text
                     ╔═════════════════════════════════╗
                     ║           sentinel-1            ║
                     ║          (Port: 26379)          ║
                     ╚════════════════╤════════════════╝
                                      │
                            Quorum 2/3 · Pub/Sub  
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
   ╔═════════════════════╗                         ╔═════════════════════╗
   ║     sentinel-2      ║◄═══════════════════════►║     sentinel-3      ║
   ║    (Port: 26379)    ║                         ║    (Port: 26379)    ║
   ╚══════════╤══════════╝                         ╚══════════╤══════════╝
              │                                               │
              └───────────────────────┬───────────────────────┘
                                      │
                                  (PING: 5s)
                           + Auto-Failover Orchestration
                                      │
                                      ▼
                     ╔═════════════════════════════════╗
                     ║     bordergate-redis-local      ║
                     ║       [PRIMARY MASTER : 6379]   ║
                     ║       (Read / Write · AOF)      ║
                     ╚════════════════╤════════════════╝
                                      │
                                      |
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
   ╔═════════════════════════════╗         ╔═════════════════════════════╗
   │ bordergate-redis-replica-1  │         │ bordergate-redis-replica-2  │
   │    [REPLICA 1 : 6380]       │         │    [REPLICA 2 : 6381]       │
   │    (Read-Only · slave)      │         │    (Read-Only · slave)      │
   ╚═════════════════════════════╝         ╚═════════════════════════════╝

```



---



### 1. Cluster Setup & Git-Friendly Strategy



#### 1.1 Git Tracking Rules (`.gitignore`)



Redis Sentinel rewrites its configuration dynamically on disk (`CONFIG REWRITE`) whenever node roles change or IDs are registered. To prevent Git branch conflicts and workspace pollution, local mutable configurations are ignored:



```gitignore

.env

.venv/

docker/sentinel1.conf

docker/sentinel2.conf

docker/sentinel3.conf

__pycache__/



# IDE & OS

.vscode/

.idea/

.DS_Store

```



---



#### 1.2 Static Base Template (`docker/sentinel.conf.example`)



An immutable template file committed to the repository:



```text

port 26379

dir "/tmp"

sentinel resolve-hostnames yes

sentinel announce-hostnames yes

sentinel monitor bordergate-master redis-local 6379 2

sentinel down-after-milliseconds bordergate-master 5000

sentinel failover-timeout bordergate-master 10000

sentinel parallel-syncs bordergate-master 1

```



---



#### 1.3 Local Node Configuration Generation



Initialize the 3 separate configuration files from the static template before launching Docker Compose:



```bash

cp docker/sentinel.conf.example docker/sentinel1.conf

cp docker/sentinel.conf.example docker/sentinel2.conf

cp docker/sentinel.conf.example docker/sentinel3.conf

```



---


### 2. Cluster Deployment & Validation



#### 2.1 Launch Services



```bash

docker compose -f docker/docker_compose.yml down

docker compose -f docker/docker_compose.yml up -d

```



---



#### 2.2 Verify Container Health



```bash

docker compose -f docker/docker_compose.yml ps

```



*Expected Result:* All 6 containers (`bordergate-redis-local`, `bordergate-redis-replica-1`, `bordergate-redis-replica-2`, `bordergate-sentinel-1`, `bordergate-sentinel-2`, `bordergate-sentinel-3`) must report status `Up`.



---



#### 2.3 Inspect Sentinel Topology Logs



```bash

docker logs bordergate-sentinel-1 | tail -n 20

```



*Key Validation Entries:*

- `Sentinel new configuration saved on disk`

- `+monitor master bordergate-master redis-local 6379 quorum 2`

- `+slave slave 172.22.0.X:6379 ...` (Discovered both replicas)

- `+sentinel sentinel ...` (Discovered the other 2 Sentinel peers)



---



#### 2.4 Query Master State from Sentinel CLI



```bash

docker exec -it bordergate-sentinel-1 redis-cli -p 26379 sentinel master bordergate-master

```



*Required Verification Values:*

- `flags`: `"master"`

- `ip`: `"redis-local"`

- `num-slaves`: `"2"`

- `num-other-sentinels`: `"2"`

- `quorum`: `"2"`



---



### 3. Data Ingestion & Replication Verification



#### 3.1 Run Consumer Ingestion



Process passenger events through the consumer:



```bash

uv run python -m src.consumer BOX-001

```



---



#### 3.2 Inspect Primary Node (Master)



Verify that the keys and secondary review priority queue have been ingested in `redis-local`:



```bash

# List all generated keys

docker exec -it bordergate-redis-local redis-cli KEYS "*"



# Inspect secondary review priority queue

docker exec -it bordergate-redis-local redis-cli ZRANGE secondary_review:ranking 0 -1 WITHSCORES

```



---



#### 3.3 Verify Asynchronous Replication on Secondary Nodes



Check the exact same data structures directly against both replicas:



```bash

# Query Replica 1 (Port 6380)

docker exec -it bordergate-redis-replica-1 redis-cli ZRANGE secondary_review:ranking 0 -1 WITHSCORES



# Query Replica 2 (Port 6381)

docker exec -it bordergate-redis-replica-2 redis-cli ZRANGE secondary_review:ranking 0 -1 WITHSCORES

```



*Expected Result:* Both replicas return the identical set of passengers and risk scores as the master.



---



#### 3.4 Verify Read-Only Enforcement on Replicas

Verify that client writes directly targeting a replica are strictly rejected:


```bash

docker exec -it bordergate-redis-replica-1 redis-cli SET test_bypass "unauthorized"

```

*Expected Output:*



```text

(error) READONLY You can't write against a read only replica.

```
---



### 4. High Availability Testing



#### 4.1 Automated Failover Under Unplanned Crash



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



#### 4.2 Fully Manual Failover 



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


5. **Restart Sentinels and sync topology:**

   ```bash

   docker start bordergate-sentinel-1 bordergate-sentinel-2 bordergate-sentinel-3

   docker exec -it bordergate-sentinel-1 redis-cli -p 26379 sentinel monitor bordergate-master redis-replica-1 6379 2

   docker exec -it bordergate-sentinel-1 redis-cli -p 26379 sentinel get-master-addr-by-name bordergate-master

   ```



---



### 5. Topology Reset to Baseline State



To return the entire deployment back to its initial declarative architecture where `bordergate-redis-local` acts as the primary master:



```bash

docker compose -f docker/docker_compose.yml down

docker compose -f docker/docker_compose.yml up -d

```



Confirm that the original master has regained its primary role:



```bash

docker exec -it bordergate-redis-local redis-cli INFO replication | grep role

# Expected output: role:master



docker exec -it bordergate-sentinel-1 redis-cli -p 26379 sentinel get-master-addr-by-name bordergate-master

# Expected output: points back to redis-local / 172.22.0.2

```