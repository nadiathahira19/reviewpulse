# ReviewPulse

Multi-tenant review analytics platform. Each business (tenant) uploads customer
reviews and gets sentiment analytics, powered by a fine-tuned IndoBERT model.

**Status:** work in progress.

## Local setup

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
pre-commit install
pre-commit install --hook-type commit-msg
```

## Run

Docker Desktop must be running before `docker compose up`.

```
docker compose up -d
uvicorn app.main:app --reload --app-dir api
```

The health check is at http://localhost:8000/healthz.

## Test

```
pytest
```
