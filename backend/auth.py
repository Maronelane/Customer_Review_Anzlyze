"""
JWT Authentication for AnZlyze.
"""
import os
from functools import wraps
from datetime import datetime, timedelta, timezone

import bcrypt
from flask import request, jsonify
from jose import jwt, JWTError

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-key-anzlyze")
ACCESS_EXPIRY_HOURS = 24
REFRESH_EXPIRY_DAYS = 30


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_tokens(user_id: str, username: str):
    now = datetime.now(timezone.utc)
    access_payload = {
        "sub": user_id,
        "username": username,
        "type": "access",
        "exp": now + timedelta(hours=ACCESS_EXPIRY_HOURS),
        "iat": now,
    }
    refresh_payload = {
        "sub": user_id,
        "username": username,
        "type": "refresh",
        "exp": now + timedelta(days=REFRESH_EXPIRY_DAYS),
        "iat": now,
    }
    access_token = jwt.encode(access_payload, SECRET_KEY, algorithm="HS256")
    refresh_token = jwt.encode(refresh_payload, SECRET_KEY, algorithm="HS256")
    return access_token, refresh_token


def decode_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid authorization header"}), 401
        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_token(token)
            if payload.get("type") != "access":
                return jsonify({"error": "Invalid token type"}), 401
            request.current_user = {
                "user_id": payload["sub"],
                "username": payload["username"],
            }
        except JWTError:
            return jsonify({"error": "Invalid or expired token"}), 401
        return f(*args, **kwargs)
    return decorated
