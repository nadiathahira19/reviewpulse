import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.security import (
    create_access_token,
    decode_access_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_password,
)

KEY = "unit-test-signing-key-0123456789abcdef"  # pragma: allowlist secret
OTHER_KEY = "another-test-signing-key-0123456789abc"  # pragma: allowlist secret


def test_password_roundtrip() -> None:
    password_hash = hash_password("a long test phrase")
    assert password_hash != "a long test phrase"  # pragma: allowlist secret
    assert verify_password(password_hash, "a long test phrase")
    assert not verify_password(password_hash, "another phrase")


def test_verify_password_rejects_a_broken_hash() -> None:
    assert not verify_password("not-a-real-hash", "anything")


def test_api_keys_are_unique_and_prefixed() -> None:
    first = generate_api_key()
    second = generate_api_key()
    assert first != second
    assert first.startswith("rp_")


def test_api_key_hash_is_stable_and_fits_the_column() -> None:
    api_key = generate_api_key()
    assert hash_api_key(api_key) == hash_api_key(api_key)
    assert hash_api_key(api_key) != api_key
    assert len(hash_api_key(api_key)) == 64


def test_token_roundtrip() -> None:
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    token = create_access_token(user_id, tenant_id, KEY)
    claims = decode_access_token(token, KEY)
    assert claims is not None
    assert claims.user_id == user_id
    assert claims.tenant_id == tenant_id


def test_token_with_a_different_key_is_rejected() -> None:
    token = create_access_token(uuid.uuid4(), uuid.uuid4(), KEY)
    assert decode_access_token(token, OTHER_KEY) is None


def test_expired_token_is_rejected() -> None:
    token = create_access_token(uuid.uuid4(), uuid.uuid4(), KEY, expires_in=timedelta(seconds=-1))
    assert decode_access_token(token, KEY) is None


def test_garbage_token_is_rejected() -> None:
    assert decode_access_token("not.a.token", KEY) is None


def test_token_without_tenant_id_is_rejected() -> None:
    payload = {"sub": str(uuid.uuid4()), "exp": datetime.now(UTC) + timedelta(minutes=5)}
    token = jwt.encode(payload, KEY, algorithm="HS256")
    assert decode_access_token(token, KEY) is None
