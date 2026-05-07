# Personal Agent Backend

FastAPI, LangGraph, LangChain, and Neon Postgres runtime for the recursive personal planner agent.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Set:

- `DATABASE_URL`: Neon pooled connection string.
- `MIGRATION_DATABASE_URL`: Neon direct connection string for Alembic.
- `CORS_ORIGINS`: comma-separated frontend origins.

## Database

```bash
alembic upgrade head
python -m app.seed
```

## Run

```bash
uvicorn app.main:app --reload
```

The backend runs at `http://localhost:8000`.

## Deploy

```bash
vercel --prod
```

