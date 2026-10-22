"""Security helpers: passwords, API keys, and access tokens."""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_password_hasher = PasswordHasher()

API_KEY_PREFIX = "rp_"  # pragma: allowlist secret
TOKEN_ALGORITHM = "HS256"


@dataclass(frozen=True)
class TokenClaims:
    """The facts we read from a valid access token."""

    user_id: uuid.UUID
    tenant_id: uuid.UUID


def hash_password(password: str) -> str:
    """Return an Argon2 hash of the password."""
    return _password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Return True only if the password matches the hash."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def generate_api_key() -> str:
    """Create a new random API key. Show it once, store only its hash."""
    return API_KEY_PREFIX + secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """Return the SHA-256 hash (64 hex characters) that is stored in the database."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def create_access_token(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    signing_key: str,
    expires_in: timedelta = timedelta(minutes=30),
) -> str:
    """Create a signed token that carries the user id and the tenant id."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "iat": now,
        "exp": now + expires_in,
    }
    return jwt.encode(payload, signing_key, algorithm=TOKEN_ALGORITHM)


def decode_access_token(token: str, signing_key: str) -> TokenClaims | None:
    """Return the claims of a valid token, or None if anything is wrong with it."""
    try:
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=[TOKEN_ALGORITHM],
            options={"require": ["exp", "sub", "tenant_id"]},
        )
        return TokenClaims(
            user_id=uuid.UUID(payload["sub"]),
            tenant_id=uuid.UUID(payload["tenant_id"]),
        )
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
