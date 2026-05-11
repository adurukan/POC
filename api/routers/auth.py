"""Teacher login — dev-only, hardcoded credentials.

This is not real authentication. There is no token issued, no session cookie,
no header verification on subsequent requests. The frontend simply remembers
"logged in" in localStorage. Replace with real auth before any deployment.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

# Hardcoded by request. Move to env or a real users table before any deployment.
_TEACHER_USERNAME = "ezgi"
_TEACHER_PASSWORD = "ezgi1234"


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    ok: bool
    username: str


@router.post("/teacher/login", response_model=LoginResponse)
def teacher_login(body: LoginRequest) -> LoginResponse:
    if body.username == _TEACHER_USERNAME and body.password == _TEACHER_PASSWORD:
        return LoginResponse(ok=True, username=body.username)
    raise HTTPException(status_code=401, detail="Geçersiz kullanıcı adı veya parola.")
