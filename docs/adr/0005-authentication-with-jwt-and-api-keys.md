# ADR 0005: Authenticate with JWT for users and API keys for programs

- Status: Accepted
- Date: 2026-10-22

## Context
Every request must be tied to exactly one tenant, and a tenant must never see
another tenant's data. People use the web interface, and customers' programs
send reviews to the API. Both need a way to prove which tenant they belong to.

## Decision
- Users log in with email and password and receive a JSON Web Token (JWT). The
  token carries the user id, the tenant id, and an expiry time. It is signed
  with a secret that comes from an environment variable (`JWT_SECRET`), never
  from the repository. PyJWT is used to create and check tokens.
- Programs send an API key. Only a SHA-256 hash of the key is stored
  (`api_keys.key_hash`), and a key can be revoked (`revoked_at`).
- Passwords are stored as Argon2 hashes (argon2-cffi).
- The tenant is always taken from the token or the API key, never from data
  sent by the client.

## Alternatives considered
- Server-side sessions: easy to cancel, but every request needs a session
  lookup and it suits browsers more than programs.
- An external login provider: less code to write, but it adds a service, a
  cost, and a dependency that is too much for this project.

## Consequences
- A JWT cannot be cancelled before it expires, so tokens get a short lifetime.
- `JWT_SECRET` must be set in every environment and must never be committed.
  If it leaks, all tokens can be forged.
- The tenant rule is tested later (task 11): a request from tenant A must never
  read tenant B's data.
- Two more dependencies to keep up to date.

## References
- PyJWT: https://pyjwt.readthedocs.io/en/stable/
- argon2-cffi: https://argon2-cffi.readthedocs.io/en/stable/
