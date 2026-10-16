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
│   ├── reference_examples/         # Synthetic Pub/Sub event samples
│   └── seed_data/                  # Synthetic data as initial CSV files
├── docker/
│   └── docker-compose.yml          # Local Redis Docker infrastructure & redisnet network
├── src/
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
# The endpoint domain provided by your Redis Cloud database instance
REDIS_CLOUD_HOST=your-redis-cloud-endpoint.db.redis.io

# Public port assigned to your Redis Cloud database (e.g., 12438)
REDIS_CLOUD_PORT=12438

# Username for Redis ACL authentication (default is usually 'default')
REDIS_CLOUD_USER=your_user

# Authentication password for your Redis Cloud instance
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
uv run python src/test_connect.py
```