"""
Web UI Authentication — simple password + HMAC token.
"""
import hashlib
import hmac
import time
import json
import base64
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    token: str
    expires_in: int  # seconds


def _sign(payload: str) -> str:
    """HMAC-SHA256 sign a payload."""
    return hmac.new(
        settings.WEB_TOKEN_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()


def create_token() -> str:
    """Create a signed token valid for 24 hours."""
    now = int(time.time())
    expires = now + 86400  # 24h
    payload = json.dumps({"exp": expires, "iat": now})
    sig = _sign(payload)
    token_data = json.dumps({"p": payload, "s": sig})
    return base64.urlsafe_b64encode(token_data.encode()).decode().rstrip("=")


def verify_token(token: str) -> bool:
    """Verify a signed token. Returns True if valid and not expired."""
    try:
        # Pad base64 (urlsafe b64decode needs correct padding)
        padding = (-len(token) % 4)
        padded = token + "=" * padding if padding else token
        data = json.loads(base64.urlsafe_b64decode(padded))
        payload = data["p"]
        sig = data["s"]
        expected = _sign(payload)
        if not hmac.compare_digest(sig, expected):
            return False
        claims = json.loads(payload)
        return claims.get("exp", 0) > time.time()
    except Exception:
        return False


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """Authenticate with web UI password. Returns a session token."""
    if req.password != settings.WEB_PASSWORD:
        raise HTTPException(status_code=401, detail="密码错误")
    token = create_token()
    return TokenResponse(token=token, expires_in=86400)


@router.get("/verify")
async def verify():
    """Verify the current token is valid. Token passed via Authorization header."""
    # Token validation happens in middleware/dependency; if we get here, it's valid.
    return {"valid": True}
