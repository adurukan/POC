import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.agent_runtime import agent_lifespan
from api.routers.auth import router as auth_router
from api.routers.questions import router as questions_router
from api.routers.teacher import router as teacher_router

_API_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _API_DIR.parent

# Ensure the static-served directories exist at import time so the StaticFiles
# mount doesn't fail when the app is first started on a fresh checkout.
(_API_DIR / "visuals").mkdir(parents=True, exist_ok=True)
(_API_DIR / "visuals" / "teacher").mkdir(parents=True, exist_ok=True)

app = FastAPI(lifespan=agent_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/visuals", StaticFiles(directory=str(_API_DIR / "visuals")), name="visuals")
app.include_router(questions_router, prefix="/questions")
app.include_router(auth_router)
app.include_router(teacher_router)

(_REPO_ROOT / "openapi.json").write_text(json.dumps(app.openapi(), indent=2))
