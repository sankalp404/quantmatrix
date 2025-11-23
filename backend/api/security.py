from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt

from backend.config import settings

# Single algorithm constant for the whole app
JWT_ALGORITHM = "HS256"


def get_secret_key() -> str:
    return getattr(settings, "SECRET_KEY", "fallback-secret-key-for-development")


def create_access_token(claims: Dict[str, Any], expires: Optional[timedelta] = None) -> str:
    payload = dict(claims)
    exp = datetime.utcnow() + (expires or timedelta(minutes=getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 30)))
    payload["exp"] = exp
    return jwt.encode(payload, get_secret_key(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, get_secret_key(), algorithms=[JWT_ALGORITHM])


