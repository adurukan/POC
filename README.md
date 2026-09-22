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
  limbas/
    README.md
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

## Local Dev: Step by Step

Run all commands from repo root unless noted otherwise.

### 1) Start Docker services (DB + bootstrap + admin panel)

```bash
docker compose up -d --build                 # start PostgreSQL + db-bootstrap + Limbas admin panel
```

### 2) Verify Docker health

```bash
docker compose ps                             # check that db and limbas are Up
docker compose ps -a db-bootstrap             # check that bootstrap exited successfully
docker compose logs db-bootstrap              # inspect migration + seed logs
```

What to check:

- `db` is `Up`.
- `limbas` is `Up` and healthy.
- `db-bootstrap` finished with `Exit 0`.
- Logs contain successful Alembic upgrade and `python -m db.seed all`.

### 3) Run backend (Terminal 1)

```bash
cd api                                        # enter backend folder
uv run uvicorn main:app --reload             # start FastAPI
```

### 4) Run frontend (Terminal 2)

```bash
cd web                                        # enter frontend folder
pnpm dev                                      # start Vite dev server
```

### 5) Verify DB tables and contents (Terminal 3)

```bash
docker compose exec db psql -U app -d teachingai   # open psql shell inside db container
```

Inside `psql`, run:

```sql
\conninfo                                     -- confirm current DB/user
SHOW search_path;                             -- usually "$user", public
\dt                                           -- list all tables

SELECT COUNT(*) AS questions FROM questions;
SELECT COUNT(*) AS documents FROM documents;
SELECT COUNT(*) AS sections FROM document_sections;
SELECT COUNT(*) AS packs FROM section_knowledge_packs;
SELECT COUNT(*) AS pending FROM pending_questions;
SELECT COUNT(*) AS problems FROM problems;

SELECT id, subject_name, left(question_text, 120) FROM questions ORDER BY id DESC LIMIT 5;
SELECT id, status, started_at, finished_at FROM ingestion_runs ORDER BY id DESC LIMIT 5;
```

Exit `psql`:

```sql
\q
```

### 6) (Optional) Reset everything from scratch

```bash
docker compose down -v                        # remove containers + DB volume
docker compose up -d --build                  # recreate DB and rerun bootstrap
docker compose logs db-bootstrap              # verify migrations + seed again
```

## Limbas Admin Panel

Limbas is a self-hosted low-code database UI bundled as a Docker service. It connects directly to the `teachingai` PostgreSQL database and gives teachers and content admins a browser-based interface for managing the question bank, reviewing the AI-generated question queue, and monitoring ingestion runs — no CLI or SQL needed.

**Access:** `http://localhost:8090`

**First-run:** The first time you open Limbas you will see a setup wizard. Enter the DB credentials (`host: db`, `port: 5432`, `db: teachingai`, `user: app`, `pass: app`) and create an admin account. This is a one-time step; config is persisted in the `limbas_inc` Docker volume.

See [`limbas/README.md`](limbas/README.md) for full setup instructions, recommended table configuration, and typical workflows.

### Service ports

| Service | URL |
|---|---|
| FastAPI backend | `http://localhost:8000` |
| Vite frontend (dev) | `http://localhost:5173` |
| Limbas admin panel | `http://localhost:8090` |
| PostgreSQL | `localhost:5432` |

## Manual DB Commands

### Migration (manual)

```bash
uv run alembic -c db/alembic.ini heads        # show migration heads
uv run alembic -c db/alembic.ini upgrade head # apply all migrations
uv run alembic -c db/alembic.ini current      # show current revision
```

### Seed (manual)

```bash
uv run python -m db.seed --help               # show seeder commands
uv run python -m db.seed all                  # exact-sync canonical seed tables
uv run python -m db.seed questions            # exact-sync only questions table
uv run python -m db.seed export               # export current DB into seed fixtures
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
