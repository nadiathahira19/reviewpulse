"""Find out which tenant a request belongs to."""

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_signing_key
from app.db import get_session
from app.models import ApiKey
from app.security import decode_access_token, hash_api_key


@dataclass(frozen=True)
class CurrentTenant:
    """The tenant of the current request and how it was proven."""

    tenant_id: uuid.UUID
    method: str


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def get_current_tenant(
    session: Annotated[Session, Depends(get_session)],
    signing_key: Annotated[str, Depends(get_signing_key)],
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header()] = None,
) -> CurrentTenant:
    """The tenant comes only from a token or an API key, never from the request data."""
    if authorization is not None:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer":
            raise _unauthorized()
        claims = decode_access_token(token, signing_key)
        if claims is None:
            raise _unauthorized()
        return CurrentTenant(tenant_id=claims.tenant_id, method="token")

    if x_api_key is not None:
        api_key = session.scalars(
            select(ApiKey).where(
                ApiKey.key_hash == hash_api_key(x_api_key),
                ApiKey.revoked_at.is_(None),
            )
        ).first()
        if api_key is None:
            raise _unauthorized()
        return CurrentTenant(tenant_id=api_key.tenant_id, method="api_key")

    raise _unauthorized()
