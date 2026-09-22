# Limbas Admin Panel

Limbas is a self-hosted low-code database front-end. In this project it serves as an
internal admin panel for teachers and content admins to manage the question bank,
review the AI-generated question queue, and monitor ingestion runs — all from a web UI
without needing CLI access or SQL knowledge.

## Access

Once the stack is running, Limbas is available at:

```
http://localhost:8090
```

## First-run setup (one-time)

The very first time you start Limbas it walks you through an installation wizard.
Complete these steps once:

1. Open `http://localhost:8090` in your browser.
2. You will be redirected to the Limbas installer.
3. On the **Database** step, enter:
   - Host: `db`
   - Port: `5432`
   - Database name: `teachingai`
   - User: `app`
   - Password: `app`
4. On the **Admin account** step, set a strong admin password (use the value from
   `LIMBAS_ADMIN_PASS` in your `.env`).
5. Complete the wizard. Limbas will create its own system tables inside the
   `teachingai` database (prefixed `lmb_`) — these do not interfere with any
   application tables.
6. Log in with the admin credentials you just created.

> **Note:** The installer only runs once. After setup, the configuration is persisted
> in the `limbas_inc` Docker volume. Recreating the container without removing
> that volume will skip the installer on the next start.

## Recommended table configuration

After first login, go to **Administration → Tables** and import/link the following
application tables so they appear in the Limbas UI:

| Table | Suggested access | Purpose |
|---|---|---|
| `questions` | Read + Edit | Browse and correct AI-generated questions |
| `pending_questions` | Read + Edit | Review and approve/reject the question queue |
| `documents` | Read-only | Inspect ingested textbook documents |
| `document_sections` | Read-only | Browse extracted document sections |
| `section_knowledge_packs` | Read-only | View knowledge packs linked to sections |
| `ingestion_runs` | Read-only | Monitor pipeline run history and status |
| `problems` | Read + Edit | Manage problem records |

## Typical workflows

### Approving a pending question

1. Navigate to **Tables → pending_questions**.
2. Filter by `status = queued` and the desired `subject` / `grade`.
3. Click into a row to open the detail view.
4. Read the full `question_text` and any associated metadata.
5. Change `status` to `approved` (or `rejected`) and save.

### Editing a question

1. Navigate to **Tables → questions**.
2. Search or filter by `subject_name`, `grade`, or keywords in `question_text`.
3. Click the row, click **Edit**, update the text, and save.

### Monitoring ingestion

1. Navigate to **Tables → ingestion_runs**.
2. Sort by `started_at` descending to see the most recent runs.
3. Check the `status` column for failures and inspect `finished_at` for duration.

## Stopping / removing Limbas

To stop without losing configuration:
```bash
docker compose stop limbas
```

To remove completely (including all Limbas config and data volumes):
```bash
docker compose down
docker volume rm $(docker volume ls -q | grep limbas)
```

> Removing the volumes will require running the first-run setup wizard again.

## Notes

- Limbas runs on port **8090** to avoid conflict with the FastAPI backend (8000) and
  the Vite frontend (5173).
- Limbas creates tables prefixed with `lmb_` in the `teachingai` database. These are
  Limbas system tables and are safe to ignore from the application side.
- No Alembic migration is needed — Limbas manages its own schema independently.
- For production use, place Limbas behind a reverse proxy (nginx/Caddy) and restrict
  access to internal network only.
