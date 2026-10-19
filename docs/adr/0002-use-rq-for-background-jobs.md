# ADR 0002: Use RQ for background jobs

- Status: Accepted
- Date: 2026-10-19

## Context
Analyzing a batch of reviews takes longer than a normal web request. The API
must answer quickly (`POST /batches` returns 202) and hand the work to a
background worker. We need a job queue with retries and a way to keep failed
jobs instead of losing them. We already run Redis for local development.

## Decision
Use RQ (Redis Queue) for background jobs. The API enqueues a job into Redis and
a separate worker process runs it.

## Alternatives considered
- Celery: a mature task queue with scheduling, workflows (chains, groups),
  monitoring events, and several brokers (RabbitMQ, Redis, Amazon SQS). We need
  only one kind of job with retries, so most of these features would be unused
  while adding more concepts and configuration to learn and maintain.
- Running the work inside the API process (for example FastAPI background
  tasks): simplest, but jobs would be lost if the API restarts and could not be
  scaled or retried separately.

## Consequences
- RQ needs only Redis, which is already part of the Docker Compose setup.
- Enqueuing a normal Python function is enough, so the code stays small.
- The queue is tied to Redis. If we later need complex workflows, scheduling
  across many job types, or another broker, we would have to migrate to a
  heavier tool such as Celery.
- Retry and failed-job handling will be built on RQ's features (task 16).

## References
- RQ documentation: https://python-rq.org/
- Celery, "Introduction to Celery": https://docs.celeryq.dev/en/stable/getting-started/introduction.html
