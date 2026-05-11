# TeachingAI

TeachingAI has three main parts:

- `api/` FastAPI app (serves questions)
- `pipeline/` PDF -> knowledge-pack ingestion and retrieval CLI
- `db/` single source of truth for database runtime, migrations, and canonical seeds

## Project Layout

```text
TeachingAI/
  api/
  pipeline/
  db/
    database.py
    alembic.ini
    migrations/
    seed.py
    seeds/data/
  books/
  processed/
  docker-compose.yml
  .env
```

## Database Ownership (Unified)

All DB responsibilities are centralized in `db/`:

- Shared SQLAlchemy runtime: `db/database.py`
- Unified Alembic home: `db/alembic.ini`, `db/migrations/`
- Unified canonical seeds: `db/seed.py`, `db/seeds/data/`

`api/`, `pipeline/`, and `agents/` share this DB layer.

## Run App (Backend + Frontend)

### Backend (FastAPI)

Run from repo root:

```bash
cd api                                      # enter backend folder
uv run uvicorn main:app --reload           # start FastAPI in dev mode
```

### Frontend (Vite + React)

Run from repo root:

```bash
cd web                                      # enter frontend folder
pnpm dev                                    # start Vite dev server
```

## Database Bootstrap (Auto Migrate + Auto Seed)

### 1) Start services

```bash
docker compose up -d --build                # start DB + one-shot bootstrap
docker compose ps                            # check long-running services
docker compose ps -a db-bootstrap            # confirm bootstrap exit status
```

What to check:

- `db` is `Up`.
- `db-bootstrap` runs and exits successfully (check via `docker compose ps -a db-bootstrap`).

### 2) Inspect bootstrap logs

```bash
docker compose logs db-bootstrap             # view migrate+seed logs
```

What to check:

- Alembic upgrade succeeds.
- `python -m db.seed all` succeeds.

Important:

- Canonical seed runs in **exact-sync mode** for included tables.
- Any extra local rows in those tables are removed on each bootstrap run.

## Manual DB Commands

### Migration

```bash
uv run alembic -c db/alembic.ini heads      # show migration heads
uv run alembic -c db/alembic.ini upgrade head  # apply all migrations
uv run alembic -c db/alembic.ini current    # show current revision
```

### Seed

```bash
uv run python -m db.seed --help             # show seeder commands
uv run python -m db.seed all                # exact-sync canonical seed tables
uv run python -m db.seed questions          # exact-sync questions table only
uv run python -m db.seed export             # export current DB into seed fixtures
```

### Reset everything

```bash
docker compose down -v                       # remove containers + DB volume
docker compose up -d --build                # recreate from scratch
docker compose logs db-bootstrap             # verify migration+seed success
```

## Canonical Seed Coverage

Included (exact-sync):

- `questions`
- `documents`
- `document_sections`
- `section_knowledge_packs`
- `pending_questions`
- `problems`

Excluded:

- `ingestion_runs`
- LangGraph checkpoint tables

## Pipeline CLI Commands

Run from `pipeline/`:

```bash
cd pipeline                                                                      # enter pipeline workspace
uv run python -m cli --help                                                      # list pipeline subcommands

uv run python -m cli process-pdf \                                               # render pages + marker extract + section markdown generation
  --pdf ../books/matematik_5_1.pdf \                                             # source textbook PDF
  --sections sections/matematik_5_1.yaml                                         # section range config

uv run python -m cli load-packs \                                                # upsert docs/sections/packs + embeddings into DB
  --processed-dir ../processed/matematik_5_1

uv run python -m cli search \                                                    # semantic retrieval over seeded/loaded packs
  --query "5. sınıf Geometrik Şekiller"                                          # free-text query

uv run python -m cli search --query "dikdörtgende alan" --only-validated         # search only validated packs
uv run python -m cli search --query "doğru parçası" --grade 5 --subject Matematik  # filtered search by metadata
```

What to check:

- `processed/matematik_5_1/` contains `extraction/`, `sections/`, `index/`.
- `load-packs` prints non-null `Document ID` and `Ingestion Run ID`.
- `search` returns ranked hits with similarity and metadata.

## Agents Queue Commands (Teacher Studio Backend)

Run from repo root:

```bash
uv run python -m agents.cli --help                                               # list queue/operator commands

uv run python -m agents.cli generate-batch \                                     # generate N new artifacts and queue into pending_questions
  --grade 5 --subject "Geometrik Nicelikler" --topic "Geometrik Nicelikler" --count 5

uv run python -m agents.cli queue-status                                         # show queue counts + feedback backlog

uv run python -m agents.cli replay-feedback \                                    # replay teacher feedback folders and requeue improved artifacts
  --grade 5 --subject "Geometrik Nicelikler" --limit 20
```

What to check:

- `generate-batch` prints each `req_*` row as queued with attempts summary.
- `queue-status` shows pending counts by subject/grade.
- `replay-feedback` moves processed items from `issues/feedback/` to `issues/replayed/`.
