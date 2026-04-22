Create a new FastAPI endpoint for: $ARGUMENTS

The argument format is "<action> <resource>" (e.g. "create user", "list products", "get order").

## What to create

**1. Schema file** at `/api/schemas/<resource>.py`
- If the file already exists, add to it rather than replacing it
- A `<Resource>Create` model for request body (POST/PUT only)
- A `<Resource>Response` model for the response
- All fields typed with Python type hints

**2. Router file** at `/api/routers/<resource>.py`
- If the file already exists, add the new endpoint to it
- Use `APIRouter` with a prefix of `/<resource>s` and a tag of `<resource>s`
- Import and use the schemas defined above
- Return a hardcoded placeholder response for now — no database logic yet

## Rules
- Keep it minimal: no business logic, no database calls, just structure
- Use appropriate HTTP method: POST for create, GET for list/get, PUT for update, DELETE for delete
- All functions and parameters must have type hints
- After creating both files, show me the curl command to test the endpoint
