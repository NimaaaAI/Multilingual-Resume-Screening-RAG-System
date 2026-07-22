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

### 4. Database migrations

The schema (tables/columns) is defined in `api/app/db/models.py` and version-controlled as
Alembic migration files in `api/alembic/versions/`.

`alembic.ini` and the `api/alembic/` folder were generated **once**, the first time Alembic was
set up for this project, with:
```bash
alembic init api/alembic
```
This is already done and committed to git — **do not run it again** on an existing clone (it
refuses to run if `api/alembic/` already exists/isn't empty). It's documented here only so it's
clear where those files came from.

What you actually need to run, on a fresh clone, is applying the migrations that already exist to
your own local (empty) database:
```bash
alembic upgrade head
```

### 5. Run the API

```bash
uvicorn api.app.main:app --reload
```

### 6. Run the background worker

Uploads are processed by a separate RQ worker process, not the API itself — run this in another
terminal tab (with the venv activated) whenever you want uploads to actually get processed:

```bash
rq worker --worker-class rq.worker.SimpleWorker --url redis://localhost:6379/0
```

**Why `SimpleWorker` and not the default `Worker`:** RQ's default worker forks a child process per
job for isolation. On macOS, forking *after* certain native libraries (Apple's Objective-C
runtime, and separately PyTorch's BLAS/OpenMP threading, used by the embedding model) have already
initialized is unsafe and crashes with a signal-6 abort. `SimpleWorker` runs jobs directly in the
same process instead of forking, sidestepping this — a normal, supported RQ mode, not a hack.
This is a macOS-only development quirk; it won't apply once this runs in Docker/Linux later.

### 7. Lint

```bash
ruff check .
```

## Changing the database schema (Alembic migrations)

The database tables are defined as Python classes in `api/app/db/models.py` — that file is the
source of truth for what the schema *should* look like. You never create or alter tables by hand
in `psql`. Whenever you add/change/remove a model or column, follow this exact recipe:

1. Edit `api/app/db/models.py` (add a field, add a new model class, etc.).
2. Generate a migration file — Alembic connects to the real database, compares it against the
   models, and writes a script containing only the difference:
   ```bash
   alembic revision --autogenerate -m "short description of the change"
   ```
3. **Open the generated file** in `api/alembic/versions/` and read it before applying anything —
   autogenerate is usually right but not infallible (it can miss renames, for example).
4. Apply it to your actual database:
   ```bash
   alembic upgrade head
   ```
5. Commit **both** the `models.py` change and the new migration file together — they're one unit
   of change. The migration file is the permanent record of "how did the schema get from A to B";
   losing it (unlike losing most files) can't be regenerated from the models alone once the
   database already reflects that change, since autogenerate only detects *differences* between
   models and the live database.

Useful commands for checking state:
```bash
alembic current          # which migration is the database currently stamped at
alembic history --verbose  # the full chain of migrations, oldest to newest
```
