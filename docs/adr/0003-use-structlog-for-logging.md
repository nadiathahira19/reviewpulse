# ADR 0003: Use structlog for structured logging

- Status: Accepted
- Date: 2026-10-19

## Context
The API and the background worker run as separate processes, and a problem in
one request can be hard to follow through plain text logs. We want every log
line to be machine-readable and to carry the same context (for example a
`request_id`), so that all lines for one request can be found together.

## Decision
Use structlog and write logs as JSON. Context such as `request_id` is bound
once per request, so it appears on every later log line of that request.
Logging is set up in task 13.

## Alternatives considered
- Python's standard `logging` module alone: always available, but we would have
  to write our own JSON formatting and our own way to attach request context.
  structlog can also pass its output to the standard `logging` module, so
  libraries that use `logging` keep working.
- Plain text log lines with string formatting: easy to write, but hard to search
  and parse once there are many requests.

## Consequences
- Every log line is a set of key-value pairs, so it can be filtered and parsed
  (for example by `request_id`).
- One more dependency to learn and keep up to date.
- Logging setup needs care: one shared configuration, and every new service has
  to use it.
- Log output must never contain secrets or full review texts unless we decide
  it is safe.

## References
- structlog, "Why...": https://www.structlog.org/en/stable/why.html
