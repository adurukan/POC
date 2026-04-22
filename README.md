# TeachingAI

A web application for teaching mathematics. The backend serves questions, solution steps, and visuals through an API. The frontend displays them to the student.

---

## Project Structure

```
TeachingAI/
├── docker-compose.yml
├── .env
├── .env.example
├── api/                  ← Python backend
└── web/                  ← React frontend (not created yet)
```

### Root-level files

| File | Purpose |
|---|---|
| `docker-compose.yml` | Defines and starts all services (currently just the database). One command starts everything. |
| `.env` | Secret configuration values (database credentials, etc.). Never committed to git. |
| `.env.example` | A template of `.env` with blank values. Committed to git so anyone setting up the project knows what variables they need. |

---

## The `api/` folder — Backend

Everything the frontend talks to lives here. It is a Python application built with FastAPI.

```
api/
├── main.py
├── database.py
├── pyproject.toml
├── seed.py
├── alembic.ini
├── models/
│   └── question.py
├── schemas/
│   └── question.py
├── routers/
├── visuals/
└── alembic/
    ├── env.py
    └── versions/
```

### `main.py`

The entry point of the backend. This is where the FastAPI application is created. All routers (URL endpoints) get registered here, and the `/visuals` folder is exposed so the frontend can fetch SVG files directly over HTTP.

When you run `uv run uvicorn main:app --reload`, uvicorn reads this file and starts the server.

### `database.py`

Handles the connection to PostgreSQL. It reads the `DATABASE_URL` from `.env`, creates the database engine, and provides a `get_db()` function that routes use to get a database session. Think of it as the bridge between your Python code and the database.

### `pyproject.toml`

The project's dependency and configuration file. It lists every library the backend needs (FastAPI, SQLAlchemy, etc.) and the dev tools (ruff). When you run `uv sync`, uv reads this file and installs everything.

### `seed.py`

A one-time script to populate the database with initial data. Not part of the running application — you run it manually once with `uv run python seed.py` when setting up the project.

### `alembic.ini`

The configuration file for Alembic (the migration tool). It tells Alembic where to find the migration scripts and how to connect to the database.

---

### `models/`

Contains the database table definitions. Each file describes one or more tables — their columns, types, and constraints. SQLAlchemy reads these to know the shape of the database.

This folder is kept separate because it has one job: describe the database. It does not know about HTTP, API responses, or what the frontend expects. That separation keeps the database layer clean and independent.

> When you add a new table, you add a file here.

### `schemas/`

Contains the Pydantic models — the shapes of data coming in and going out of the API. A schema for a request defines what fields are required and their types. A schema for a response defines what the API will return.

This folder is separate from `models/` because the database shape and the API shape are often different. The database might store things the API should not expose. Or the API might accept fields that do not map directly to a single table. Keeping them separate gives you that flexibility.

> When you add a new endpoint, you define its input/output shapes here.

### `routers/`

Contains the URL endpoints — the functions that run when the frontend makes an API call. Each file groups endpoints for one resource (e.g., `questions.py` would contain all `/questions` routes).

This folder is separate from `main.py` because as the application grows, putting all endpoints in one file becomes unmanageable. Each router file is focused on one area of the application.

> When you add a new endpoint, you add it here (the `/new-endpoint` skill does this for you).

### `visuals/`

A folder of SVG files served directly as static files. When the frontend requests `/visuals/elevator.svg`, FastAPI reads the file from this folder and returns it. No Python logic involved — it is just file serving.

### `alembic/`

Contains the database migration system. Migrations are version-controlled changes to the database schema. Instead of manually running SQL to add or modify tables, you describe the change in a migration file and Alembic applies it.

| Path | Purpose |
|---|---|
| `alembic/env.py` | Connects Alembic to your database and your models so it can detect schema changes |
| `alembic/versions/` | Each file here is one migration — a record of one change made to the database schema |

> Every time the database structure changes (new table, new column), a new file appears in `versions/`.

---

## How it all works together

Below is the journey of a single request: the frontend asking for a question.

```
Frontend (React)
    │
    │  GET /questions/1
    ▼
main.py
    │  FastAPI receives the request and looks up which router handles /questions
    ▼
routers/question.py
    │  The route function runs. It calls get_db() to open a database session.
    ▼
database.py
    │  Returns a live session connected to PostgreSQL
    ▼
models/question.py
    │  SQLAlchemy uses the model definition to build the SQL query:
    │  SELECT * FROM questions WHERE id = 1
    ▼
PostgreSQL (Docker)
    │  Executes the query and returns the row
    ▼
routers/question.py
    │  Receives the database row and passes it to the response schema
    ▼
schemas/question.py
    │  Pydantic validates the data and serializes it to JSON
    ▼
Frontend (React)
       Receives the JSON response and renders the question
```

The key insight: each layer has one job. The router handles HTTP. The model describes the database. The schema shapes the response. None of them do each other's job.
