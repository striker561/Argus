# Argus

One dashboard for all your queues, regardless of stack or Redis instance.

Argus is a lightweight, self-hosted queue monitoring and observability tool. Point it at your Redis instances, tell it what stack you're running, and get real-time visibility into every queue across your entire infrastructure — from a single browser tab.

---

## The Problem

You deploy your workers and hope for the best. A job fails silently. A worker dies and nobody notices. You have three services on separate Redis instances and zero visibility into any of them. You find out something went wrong when a user complains.

Argus fixes that.

---

## Features

- **Multi-Redis, multi-stack** — monitor Laravel, ARQ, and more from one dashboard
- **Real-time updates** — queue depths, worker counts, and failure rates update live via SSE
- **Failed job inspector** — inspect full job payloads, see payload size, get complexity warnings
- **Payload complexity scoring** — flags jobs carrying large objects when they should carry just an ID
- **Worker heartbeat monitoring** — know instantly if a worker went silent
- **One-click job replay** — retry failed jobs directly from the dashboard
- **Zero external dependencies** — SQLite by default, Postgres optional
- **Single command setup** — `docker-compose up` and you're done

---

## Supported Stacks

| Stack | Status |
|---|---|
| Laravel | Supported |
| ARQ (FastAPI) | Supported |
| Celery | Planned |
| BullMQ | Planned |
| Sidekiq | Planned |

---

## Quick Start

```bash
# 1. Copy the example config
cp argus.example.yaml argus.yaml

# 2. Edit argus.yaml with your Redis connections
# 3. Start Argus
docker-compose up -d

# 4. Open the dashboard
# http://localhost:6700
# Default credentials: admin / argus (you will be prompted to change this)
```

---

## Configuration

```yaml
# argus.yaml

connections:
  - name: my-laravel-app
    redis_url: ${LARAVEL_REDIS_URL}
    stack: laravel

  - name: my-fastapi-app
    redis_url: ${FASTAPI_REDIS_URL}
    stack: arq
```

Environment variables are supported inside `argus.yaml`. Reference them with `${VAR_NAME}`.

---

## Self-Hosting

Argus is designed to be self-hosted. It runs as a single Docker container with an embedded SQLite database. No external services required.

For production use with multiple users or high-traffic environments, Postgres is supported via the `database_url` config option.

```yaml
# argus.yaml (optional)
database_url: postgresql+asyncpg://user:password@localhost/argus
```

---

## Tech Stack

- **Backend** — Python, FastAPI, SQLAlchemy (async), Alembic
- **Frontend** — Next.js
- **Database** — SQLite (default), Postgres (optional)
- **Real-time** — Server-Sent Events (SSE)
- **Distribution** — Docker, Docker Compose

---

## Contributing

Argus is open source and welcomes contributions. The most valuable contributions right now are **new stack adapters**. If you run Celery, BullMQ, or Sidekiq and want to add support, open an issue first so we can align on the adapter interface.

---

## License

MIT