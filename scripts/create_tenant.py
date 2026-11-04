"""Create a tenant and one API key for local development.

Usage (PowerShell), with DATABASE_URL set:
    $env:PYTHONPATH = "api"
    python scripts/create_tenant.py "Demo Tenant"

The API key is printed once. Only its hash is stored in the database.
"""

import sys

from sqlalchemy.orm import Session

from app.db import get_engine
from app.models import ApiKey, Tenant
from app.security import generate_api_key, hash_api_key


def main(name: str) -> None:
    plain_key = generate_api_key()
    with Session(get_engine()) as session:
        tenant = Tenant(name=name)
        session.add(tenant)
        session.flush()
        session.add(
            ApiKey(
                tenant_id=tenant.id,
                name="local development",
                key_hash=hash_api_key(plain_key),
            )
        )
        session.commit()
        print(f"Tenant: {tenant.name} ({tenant.id})")
    print(f"API key (shown only once): {plain_key}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python scripts/create_tenant.py "Tenant name"')
    main(sys.argv[1])
