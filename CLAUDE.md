# CLAUDE.md

Project conventions for AI coding agents working on ReviewPulse.

## Project

Multi-tenant review analytics platform. Python 3.11+, FastAPI, PostgreSQL,
Redis, a Hugging Face IndoBERT classifier. Layout: `api/`, `worker/`, `ml/`,
`web/`, `docs/`.

## Commands

- Install: `pip install -r requirements-dev.txt`
- Run API: `uvicorn app.main:app --app-dir api --reload`
- Test: `pytest`
- Lint and format: `ruff check .` and `ruff format .`
- Type check: `mypy api`

Run lint, type check, and tests before declaring any task done.

## Rules

- Every database table has a `tenant_id`. Never write a query without it.
- Every repository method takes `tenant_id` as a required argument.
- Do not skip, delete, or weaken a test to make a change pass. Fix the cause.
- Do not add a dependency without an ADR in `docs/decisions/`.
- Do not run the real IndoBERT model in tests or CI. Use `FakeClassifier`.
- Never commit secrets. Use environment variables and `.env` (git-ignored).
- Use conventional commit messages (`feat:`, `fix:`, `docs:`, `chore:`, `test:`).
- Keep changes small: one task per branch, one branch per pull request.

## Verification

Treat AI output as a draft. For every task, check it by running the code or tests,
or by reading the official documentation, and record the result in
`docs/ai-dev-log/`.
