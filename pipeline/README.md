# Pipeline (Phase 1, Marker-Only)

This folder turns textbook PDFs into Turkish Markdown knowledge packs, then loads and retrieves them via Postgres + pgvector.

## Architecture Diagram

```text
                   +--------------------------+
                   | books/<file>.pdf         |
                   +------------+-------------+
                                |
                                v
                 +--------------+----------------+
                 | process-pdf (pipeline/cli.py) |
                 +--------------+----------------+
                                |
      +-------------------------+---------------------------+
      |                         |                           |
      v                         v                           v
+-----+------+          +-------+--------+          +-------+--------+
| pages.py   |          | marker_extractor|          | report.py      |
| PNG render |          | raw markdown    |          | extraction md  |
+------------+          +-------+--------+          +----------------+
                                |
                                v
                      +---------+---------+
                      | sectioning/builder|
                      | page-range slices |
                      +---------+---------+
                                |
                                v
                      +---------+---------+
                      | understanding/    |
                      | agent + validator |
                      +---------+---------+
                                |
                                v
                      +---------+---------+
                      | sectioning/index  |
                      | section_index.*   |
                      +---------+---------+
                                |
                                v
                 +--------------+----------------+
                 | load-packs (pipeline/cli.py)  |
                 +--------------+----------------+
                                |
                                v
                    +-----------+------------+
                    | storage/loader.py      |
                    | upserts + embeddings   |
                    +-----------+------------+
                                |
                                v
                 +--------------+----------------+
                 | search (pipeline/cli.py)      |
                 +--------------+----------------+
                                |
                                v
                     +----------+-----------+
                     | storage/search.py    |
                     | pgvector cosine topK |
                     +----------------------+
```

## Command Flow Diagram

```text
1) process-pdf
   uv run python -m cli process-pdf --pdf ... --sections ...

2) load-packs
   uv run python -m cli load-packs --processed-dir ...

3) search
   uv run python -m cli search --query "..."
```

## DB Ownership

Database runtime/migrations/seeding are centralized at top-level `db/`:

- `db/database.py`
- `db/alembic.ini`
- `db/migrations/`
- `db/seed.py`

`pipeline/` does not own Alembic or seed scripts.

## Environment

Set in repo root `.env`:

```env
DATABASE_URL=postgresql+psycopg2://app:app@localhost:5432/teachingai
OPENAI_API_KEY=...
```

Optional GPU preference:

```bash
export TORCH_DEVICE=cuda
```

## End-to-End Test Run (with checks)

Run from repo root unless noted.

### 1) Start DB

```bash
docker compose up -d
docker compose ps
```

Check:
- `db` service is `Up`.

### 2) Clean DB schema (fresh start)

```bash
docker compose exec -T db psql -U app -d teachingai -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

Check:
- Command exits without errors.

### 3) Run unified migrations

```bash
uv run --project pipeline alembic -c db/alembic.ini upgrade head
uv run --project pipeline alembic -c db/alembic.ini current
```

Check:
- Migration succeeds.
- Current revision is `20260509_0001 (head)`.

### 4) (Optional) seed API sample questions

```bash
uv run --project pipeline python -m db.seed questions
```

Check:
- Seed script completes and prints inserted count.

### 5) Process PDF

```bash
cd pipeline
uv run python -m cli process-pdf \
  --pdf ../books/matematik_5_1.pdf \
  --sections sections/matematik_5_1.yaml
```

Check files exist:

```bash
ls ../processed/matematik_5_1/extraction/marker/
ls ../processed/matematik_5_1/sections/
ls ../processed/matematik_5_1/index/
```

Expected key outputs:
- `extraction/marker/raw_extraction.md`
- `extraction/extraction_report.md`
- `sections/*.md`
- `index/section_index.json`
- `index/section_index.md`

### 6) Load packs

```bash
uv run python -m cli load-packs --processed-dir ../processed/matematik_5_1
```

Check:
- CLI prints `inserted/updated` count.
- CLI prints `Document ID` and `Ingestion Run ID`.

### 7) Run semantic search

```bash
uv run python -m cli search --query "5. sınıf Geometrik Şekiller"
uv run python -m cli search --query "doğru parçası"
uv run python -m cli search --query "çok basamaklı doğal sayılar"
uv run python -m cli search --query "dikdörtgende alan"
```

Optional filters:

```bash
uv run python -m cli search --query "geometrik şekiller" --grade 5 --subject Matematik
uv run python -m cli search --query "geometrik şekiller" --only-validated
```

Check:
- Each query returns ranked rows with similarity and metadata.

## CLI Commands

```bash
uv run python -m cli --help
uv run python -m cli process-pdf --help
uv run python -m cli load-packs --help
uv run python -m cli search --help
```
