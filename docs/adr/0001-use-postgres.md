# ADR 0001: Use Postgres as the main database

- Status: Accepted
- Date: 2026-10-19

## Context
ReviewPulse stores data for many customers (tenants). Each tenant owns users,
API keys, batches of reviews, the reviews themselves, and the predictions made
for them. These records reference each other, and one tenant must never be able
to read another tenant's data. Several processes (the API and background
workers) will read and write at the same time, and they will run as separate
services.

## Decision
Use PostgreSQL as the main database, run as a separate service (started with
Docker Compose for local development). Tenant isolation will be enforced in the application by requiring a `tenant_id` in every query.

## Alternatives considered
- SQLite: simple and needs no server, but it allows only one writer at a time
  and is designed for local storage inside a single application. Our API and
  workers write at the same time from separate processes.
- MongoDB: flexible schema, but our data is naturally relational (tenants own
  users, API keys, batches and reviews), so foreign keys and a fixed schema with
  migrations fit better than moving those relationships into application code.

## Consequences
- Relationships between tables are checked by the database (foreign keys).
- The database runs as its own service, so it has to be started and backed up
  separately. This is acceptable because Docker Compose already does it locally.
- Schema changes need migrations (planned with Alembic).
- Postgres also offers row-level security, which we could add later as a second
  layer of tenant protection. We do not use it yet.

## References
- SQLite, "Appropriate Uses For SQLite": https://www.sqlite.org/whentouse.html
- PostgreSQL, "Row Security Policies": https://www.postgresql.org/docs/current/ddl-rowsecurity.html
