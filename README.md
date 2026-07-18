# Multilingual-Resume-Screening-RAG-System

A tool for recruiters: upload a job description + a batch of resumes (English or Persian), and
get back a ranked, explained shortlist of candidates. Hybrid search + graph-entity-expansion RAG
pipeline, a reranker, an evaluation harness, and observability.

Currently under active development, phase by phase — see the repo's Issues tab for progress.

## Local development setup (Mac)

This project runs natively on macOS during development (no Docker yet — that's introduced in a
later phase). You'll need Python, Postgres with the `pgvector` extension, and Redis.

### 1. Python environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

### 2. Postgres + pgvector

```bash
brew install postgresql@17 pgvector redis
brew services start postgresql@17
brew services start redis
```

These run as background services and start automatically on login — no need to start them
manually each time. Verify they're up with:

```bash
pg_isready
redis-cli ping
```

Then create the database and enable the `pgvector` extension:

```bash
createuser --pwprompt resume_rag   # set the password to match POSTGRES_PASSWORD below
createdb resume_rag --owner=resume_rag
psql resume_rag -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 3. Environment variables

```bash
cp .env.example .env
```

The default values in `.env.example` already match the local setup above (`resume_rag` user/db,
password `changeme`). Edit `.env` if you used different values.

### 4. Run the API

```bash
uvicorn api.app.main:app --reload
```

### 5. Run tests / lint

```bash
python -m pytest
ruff check .
```
