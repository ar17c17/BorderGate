# BorderGate — Border and Passport Control System

This repository contains the implementation and data infrastructure for **BorderGate**, a border-crossing simulation and control system built using Python 3.12+, Redis (Local & Cloud), and Docker Compose.

---

## Prerequisites

- **Python 3.12+**
- **uv** (high-performance Python package and environment manager)
- **Docker Desktop** or **Docker Engine** with Docker Compose

---
## Repository Structur

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
│   └── docker-compose.yml          # Local Redis Docker infrastructure & redisnet network
├── src/
│   ├── consumer.py                 # E-Gate booth worker process
│   ├── evaluator.py                # Security rules evaluation engine
│   ├── secondary_review.py         # Priority-ranked second-line inspection monitor
│   ├── security_alerts.py          # Real-time Pub/Sub security breach listener
│   ├── seed_redis.py               # Redis Cloud & Local data loader
│   └── test_connect.py             # Connection validation script
├── .env                            # Local credentials & ports (Git ignored)
├── .env.example                    # Environment template without credentials
├── .gitignore                      # Git exclusion rules (.env, .venv)
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

docker compose -f docker/docker-compose.yml up -d

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

for i in $(seq -f "%03g" 1 12); do

    BOOTH_ID="BOX-$i" uv run python -m src.consumer &

done

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

  • Stolen Passports Blacklist                                   • Live Passenger Ingestion Queues
    ├─ SET  : blacklist:stolen_passports                            └─ LIST : queue:passengers:<booth_id> (FIFO via RPUSH/BLMOVE)
    └─ HASH : stolen:<passport_number>                           • Work-in-Progress Queues
  • Wanted Persons & Threat Ranking                                 └─ LIST : queue:passengers:processing:<booth_id>
    ├─ ZSET : blacklist:wanted_persons (Score: 1-4)              • Priority-Ranked Secondary Inspection
    └─ HASH : wanted:<passport_number>                              └─ ZSET : queue:secondary_review:ranking (Pop via ZPOPMAX)
  • Country Visa Entry Policies                                  • Local Audit Trail & Event Persistence
    └─ HASH : policy:visa:<country_code>                            └─ HASH : log:<YYYY-MM-DD>:<ticket_number> (7-Day TTL) CHEEEEEEEEEEEECK
  • Active Officer Sessions & Mapping
    ├─ HASH : session:agent:<badge_number> (With TTL) CHEEEEEEEEECK
    └─ STRING: cabin:active:<booth_id> -> badge_number
  • Real-Time Security Breach Alerts
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
| **Cloud** | `session:agent:<badge_number>` | `HASH` | `HGETALL`, `EXPIRE` | Active police officer credentials and session metrics . |
| **Cloud** | `cabin:active:<booth_id>` | `STRING` | `GET`, `SET` | Maps booth ID to officer badge number. |
| **Cloud** | `alerts:security_breach` | `Pub/Sub` | `PUBLISH`, `SUBSCRIBE` | Real-time alert broadcast channel for high-level breaches (SUB). |
| **Local** | `queue:passengers:<booth_id>` | `LIST` | `RPUSH`, `BLMOVE` | Per-booth incoming passenger buffer (FIFO queue). |
| **Local** | `queue:passengers:processing:<booth_id>` | `LIST` | `BLMOVE`, `LREM` | Atomic in-flight processing list for resilience against crashes. |
| **Local** | `queue:secondary_review:ranking` | `ZSET` | `ZADD`, `ZPOPMAX` | Priority queue ordered by dynamic risk score (`(50 if not nfc_valid) + (100 - bio_score * 100)`). |
| **Local** | `log:<YYYY-MM-DD>:<ticket_number>` | `HASH` | `HSET`, `EXPIRE` | Audit trail per passenger check with a 7-day TTL expiration. |