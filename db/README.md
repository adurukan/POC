# DB Module

Single home for database runtime, migrations, and canonical seeds.

## Contents

- `database.py`: shared SQLAlchemy runtime (`Base`, `engine`, `SessionLocal`)
- `alembic.ini` + `migrations/`: unified migration history
- `seed.py`: canonical seed CLI (exact-sync + export)
- `seeds/data/`: committed seed fixtures + manifest

## Automatic Bootstrap on Docker Up

`docker compose up -d` now runs a one-shot `db-bootstrap` service that does:

1. `alembic -c db/alembic.ini upgrade head`
2. `python -m db.seed all`

`db` stays up; `db-bootstrap` exits after finishing.

Important: `db.seed all` is **exact-sync** for canonical tables and removes rows not in seed fixtures.

## Manual Migration Commands

Run from repo root:

```bash
uv run alembic -c db/alembic.ini heads
uv run alembic -c db/alembic.ini upgrade head
uv run alembic -c db/alembic.ini current
```

## Seed Commands

Run from repo root:

```bash
uv run python -m db.seed --help
uv run python -m db.seed all
uv run python -m db.seed questions
uv run python -m db.seed export
```

## Reset + Rebuild Flow

```bash
docker compose down -v
docker compose up -d --build
docker compose ps
docker compose ps -a db-bootstrap
docker compose logs db-bootstrap
```

## Canonical Seed Tables

Included in exact-sync:

- `questions`
- `documents`
- `document_sections`
- `section_knowledge_packs`
- `pending_questions`
- `problems`

Excluded:

- `ingestion_runs`
- LangGraph checkpoint tables
