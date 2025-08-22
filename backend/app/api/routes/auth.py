"""Auth API routes — register, login, token."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db_session
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str | None = None


@router.post("/register")
async def register(body: RegisterRequest):
    async with get_db_session() as session:
        existing = (await session.execute(
            select(User).where(User.username == body.username)
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
        user = User(
            username=body.username,
            email=body.email,
            hashed_password=hash_password(body.password),
        )
        session.add(user)
        await session.flush()
        return {"message": "User created", "username": user.username, "id": user.id}


@router.post("/login")
async def login(body: LoginRequest):
    async with get_db_session() as session:
        result = await session.execute(select(User).where(User.username == body.username))
        user = result.scalar_one_or_none()
        if not user or not verify_password(body.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = create_access_token(user.username)
        return {"access_token": token, "token_type": "bearer", "username": user.username}


@router.get("/me")
async def me():
    """Placeholder — full JWT middleware added in Phase 11."""
    return {"message": "Auth endpoint active. JWT middleware enabled in Phase 11."}
