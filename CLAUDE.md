# Project

A web application with a Python backend and React frontend.

## Stack

**Backend:** FastAPI, Pydantic, PostgreSQL  
**Frontend:** React, TypeScript, pnpm  
**Infrastructure:** Docker Compose  
**Python tooling:** uv

## Structure

```
/api      - FastAPI backend
/web      - React + TypeScript frontend
```

## Commands

### Backend (from /api)
```bash
uv sync                          # install dependencies
uv run uvicorn main:app --reload # start dev server
uv run pytest                    # run tests
uv run alembic upgrade head      # apply migrations
uv run alembic revision --autogenerate -m "description"  # new migration
```

### Frontend (from /web)
```bash
pnpm install   # install dependencies
pnpm dev       # start dev server
pnpm build     # production build
```

## Conventions

- Keep files minimal — extend only when needed
- Backend models use Pydantic
- All services run via Docker Compose in production
- Use pnpm (never npm), use uv (never pip directly)
