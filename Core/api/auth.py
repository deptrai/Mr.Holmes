"""Core/api/auth.py — JWT authentication for REST API."""
import jwt
import time
import os
from datetime import datetime, timedelta
from typing import Optional

SECRET_KEY = os.environ.get("MH_API_SECRET", "mr-holmes-dev-secret-change-me")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

# Simple in-memory user store (replace with DB in production)
_USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "analyst": {"password": "analyst123", "role": "analyst"},
}

def authenticate(username: str, password: str) -> Optional[dict]:
    user = _USERS.get(username)
    if user and user["password"] == password:
        return {"username": username, "role": user["role"]}
    return None

def create_token(user: dict) -> str:
    payload = {
        "sub": user["username"],
        "role": user["role"],
        "exp": int(time.time()) + TOKEN_EXPIRE_HOURS * 3600,
        "iat": int(time.time()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"username": payload["sub"], "role": payload["role"]}
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
