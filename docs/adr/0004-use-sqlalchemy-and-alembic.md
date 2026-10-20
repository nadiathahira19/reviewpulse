# ADR 0004: Use SQLAlchemy and Alembic for database access and migrations

- Status: Accepted
- Date: 2026-10-20

## Context
The API needs to read and write Postgres (see ADR 0001), and the database
structure will change as the project grows. Every table must carry a
`tenant_id`, and the database structure must be reproducible from the
repository, not only on one machine.

## Decision
Use SQLAlchemy 2.x (ORM) to define tables as Python classes and to query them.
Use Alembic to keep the database structure under version control as migration
files. Use psycopg 3 as the Postgres driver.

## Alternatives considered
- Plain SQL through a driver only: full control, but we would write and keep
  every query by hand, and we would need our own way to track which structure
  changes were already applied.
- Creating tables from code on startup, without migrations: simple at first,
  but it does not change tables that already exist, so structure changes would
  need manual work on every database.

## Consequences
- Table definitions live in Python and can be tested.
- Every structure change is a migration file in the repository, so a new
  database can be built from nothing with one command.
- Alembic is part of the SQLAlchemy project and needs SQLAlchemy 2.0 or later.
- There is more to learn than with plain SQL (ORM sessions, migration files).
- A `tenant_id` is required in every query. This rule is also written in
  `CLAUDE.md`.

## References
- SQLAlchemy introduction: https://docs.sqlalchemy.org/en/20/intro.html
- Alembic installation and basics: https://alembic.sqlalchemy.org/en/latest/front.html
