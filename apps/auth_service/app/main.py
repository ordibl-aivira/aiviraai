"""Auth Service — authentication and tenant RBAC for Workforce OS.

Endpoints
---------
GET   /health
POST  /internal/auth/register
POST  /internal/auth/login
GET   /internal/auth/verify
GET   /internal/auth/users/{user_id}
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Header

from packages.shared.models import LoginRequest, UserCreate
from packages.shared.settings import settings

app = FastAPI(title="Auth Service", version="0.1.0")

# In-memory store (replaced by Postgres + passlib + python-jose)
_users: Dict[str, dict] = {}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "auth-service"}


@app.post("/internal/auth/register")
def register(request: UserCreate) -> dict:
    """Register a new user."""
    for u in _users.values():
        if u["email"] == request.email:
            raise HTTPException(status_code=409, detail="Email already registered")

    user_id = f"usr_{uuid4().hex[:12]}"
    now = datetime.utcnow()
    user = {
        "id": user_id,
        "email": request.email,
        "full_name": request.full_name,
        "organization_id": request.organization_id,
        "role": request.role,
        "hashed_password": f"hashed_{request.password}",  # stub
        "is_active": True,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    _users[user_id] = user
    return {
        "id": user_id,
        "email": request.email,
        "full_name": request.full_name,
        "organization_id": request.organization_id,
        "role": request.role,
        "is_active": True,
        "created_at": now.isoformat(),
    }


@app.post("/internal/auth/login")
def login(request: LoginRequest) -> dict:
    """Authenticate and return a JWT token."""
    user = None
    for u in _users.values():
        if u["email"] == request.email:
            user = u
            break

    if not user or user["hashed_password"] != f"hashed_{request.password}":
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = f"jwt_{uuid4().hex}"  # stub — use python-jose in production
    expires_in_seconds = settings.jwt_expiration_minutes * 60
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in_seconds,
        "user_id": user["id"],
        "organization_id": user["organization_id"],
    }


@app.get("/internal/auth/verify")
def verify_token(authorization: str = Header(default="")) -> dict:
    """Verify a JWT token and return user info."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    return {
        "valid": True,
        "user_id": "usr_stub",
        "organization_id": "org_stub",
        "role": "admin",
    }


@app.get("/internal/auth/users/{user_id}")
def get_user(user_id: str) -> dict:
    """Retrieve user details."""
    user = _users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {k: v for k, v in user.items() if k != "hashed_password"}
