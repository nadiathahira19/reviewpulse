# Dev log

Each entry records a task I gave to an AI assistant, what came back, what was
wrong, and how I checked it.


## 2026-10-17: Ruff import-order error (I001)

- **Task given to the assistant:** set up ruff (lint and format) and mypy for the
  FastAPI skeleton.
- **Result:** `ruff check` reported I001 (imports not sorted) in
  `api/tests/test_health.py`. Ruff treated `app` as a third-party package.
- **What went wrong:** ruff could apply an auto-fix, but that would only hide the
  cause. The real problem was that ruff did not know where our own code lives.
- **How I fixed and checked it:** added `src = ["api"]` to `pyproject.toml`, so
  `app` is treated as first-party. Re-ran `ruff check` and `ruff format --check`
  until both passed. `ruff format` also added a missing final newline to files.
- **Time spent:** not tracked

## 2026-10-17: pre-commit failed to build its environment on Windows

- **Task given to the assistant:** add pre-commit hooks (ruff, ruff-format, and
  basic file checks).
- **Result:** the config was added, but the first `pre-commit run --all-files`
  stopped with a `FileNotFoundError` raised by virtualenv while building a hook
  environment. Python is the Microsoft Store build on Windows.
- **What went wrong:** the cause is not confirmed. The assistant suspected the
  260-character Windows path limit, because the error appeared while copying
  files from a very long path. I worked around it by setting
  `$env:VIRTUALENV_APP_DATA` to a short folder for that terminal session.
- **How I checked it:** re-ran `pre-commit run --all-files`. The hooks built and
  ran. The end-of-file hook failed once because it modified files, and the next
  run passed. Later commits were also rejected twice because a hook changed a
  staged file. I staged the file again and committed.
- **Time spent:** not tracked

## 2026-10-17: Two wrong suggestions from the assistant

- **Task given to the assistant:** guide me step by step through Week 1 and tell
  me which command to type next.
- **Result:** the steps mostly worked, but two suggestions were wrong.
- **What went wrong:**
  1. It suggested `cd /d "D:\..."` to change drive. That is a cmd.exe option.
     In PowerShell it fails, and plain `cd "D:\..."` is correct.
  2. It named Docker Compose as the next task, but my plan lists the GitHub
     Actions workflow (task 5) first. It had left task 5 out of its own summary.
- **How I checked it:** the first one failed with an error in my terminal. The
  second one I noticed when my Excel plan was compared with the assistant's list.
- **Time spent:** not tracked

## 2026-10-20: detect-secrets flagged names, not secrets

- **Task given to the assistant:** add the detect-secrets hook to pre-commit.
- **Result:** the hook stopped my commit because it flagged the database password
  line in `docker-compose.yml` as a secret. The same thing happened again on
  2026-10-22, when I added authentication code: it flagged the API key prefix
  constant in `security.py` and the test keys.
- **What went wrong:** the flagged lines were not real secrets. The hook reacts to
  variable names that contain words like "key" or "password". They were a
  database password for local Docker only, a key prefix constant, and keys used
  only inside tests.
- **How I fixed and checked it:** I added an inline `# pragma: allowlist secret`
  comment to those specific lines, instead of excluding whole files from the
  hook. I re-ran the commit and the hook passed. The real signing key and the
  database URL are only read from environment variables and are not in the repo.
- **Time spent:** not tracked

## 2026-10-20: ADR 0003 was merged as an empty file

- **Task given to the assistant:** write ADR 0003 (use structlog for logging).
- **Result:** the pull request was merged on 2026-10-19, but
  `docs/adr/0003-use-structlog-for-logging.md` on `main` had no content.
- **What went wrong:** most likely the file was not saved in the editor when I
  committed, so an empty file was committed. This is my assumption. I did not
  check the editor state at that moment.
- **How I found and fixed it:** I noticed it in the commit summary, which showed
  no added lines for that file, and confirmed it with `git show origin/main:`
  on the file. I fixed it in a follow-up pull request (#11), together with the
  detect-secrets change. Since then I run `git status` before committing and
  save all files first.
- **Time spent:** not tracked

## 2026-10-21: pre-commit mypy could not find sqlalchemy and alembic

- **Task given to the assistant:** write the database models for the schema with
  SQLAlchemy, and later the Alembic migration setup.
- **Result:** the mypy hook had worked since 2026-10-17. After I added SQLAlchemy
  code, it failed with `import-not-found` for `sqlalchemy`. The next day it
  failed in the same way for `alembic`.
- **What went wrong:** the mypy hook runs in its own isolated environment, and the
  assistant's config only listed the libraries from the first version of the
  project in `additional_dependencies`. The same `mypy` command passed in my own
  virtualenv, where the libraries were installed, so only the commit-time hook
  caught it. The assistant made this mistake twice.
- **How I fixed and checked it:** added each library to `additional_dependencies`
  in `.pre-commit-config.yaml` and committed again until the hook passed. Later I
  added `pyjwt`, `argon2-cffi` and `structlog` in the same commit that introduced
  them, and the hook passed the first time.
- **Still to do:** write a rule about `additional_dependencies` in `CLAUDE.md`.
- **Time spent:** not tracked

## 2026-10-23: pre-commit failed to build its environment again

- **Task given to the assistant:** add `structlog` and commit the change.
- **Result:** changing `additional_dependencies` made pre-commit build a new mypy
  environment, and the commit stopped with the same virtualenv `FileNotFoundError`
  as in Week 1. The missing file was under the `LocalCache` folder of the
  Microsoft Store Python.
- **What went wrong:** I had opened a new terminal, so `$env:VIRTUALENV_APP_DATA`
  was no longer set. The root cause is still not confirmed. It looks related to
  where the Store Python keeps its cache, and the path length idea from Week 1 is
  still only a suspicion.
- **How I fixed and checked it:** set `$env:VIRTUALENV_APP_DATA = "D:\vcache"` in
  the new terminal and committed again. The environment was built and all hooks
  passed.
- **Time spent:** not tracked

## 2026-10-23: A leftover MODEL_NAME made a test fail, and the planned fix was never committed

- **Task given to the assistant:** connect a real IndoBERT sentiment model to
  `/reviews/analyze`, selected with the `MODEL_NAME` environment variable.
- **Result:** I tried the real model in my terminal by setting `$env:MODEL_NAME`.
  Afterwards `pytest` showed one failing test in `test_analyze.py`, the one that
  expects the fake analyzer (`fake-keyword-v0`).
- **What went wrong:** the variable was still set in the same PowerShell session,
  so the app loaded the real model during the tests. I checked this with
  `echo $env:MODEL_NAME`, which printed the model name. I did not read the
  failure message itself, so the explanation rests on that check. The planned fix
  was a `api/tests/conftest.py` fixture that removes `MODEL_NAME` before every
  test. The pull request description and this log said it was added, but on
  2026-10-29 `git ls-files` showed the file was never committed. Most likely the
  `git add` for that file failed because the file did not exist yet, and neither
  of us noticed. CI stayed green because CI never sets `MODEL_NAME`, so nothing
  caught it. I found it while applying the batch upload changes, which needed
  that file.
- **How I fixed and checked it:** on 2026-10-23 I unset the variable with
  `Remove-Item Env:MODEL_NAME` and all tests passed again (46 passed, 1 skipped
  locally). On 2026-10-29 I created `api/tests/conftest.py` with the fixture and
  checked with `git ls-files` and `git status` that the file is tracked. From now
  on I check that every file I mean to commit shows up in `git status` before I
  commit.
- **Time spent:** not tracked

## 2026-10-23: A deprecation warning I have not verified

- **Task given to the assistant:** keep the test suite clean while adding the API
  endpoints.
- **Result:** every `pytest` run in CI shows `StarletteDeprecationWarning`: using
  `httpx` with `starlette.testclient` is deprecated, install `httpx2` instead. The
  tests pass.
- **What went wrong:** the assistant told me the warning does not fail the tests
  and moved on. Neither of us has checked the Starlette or FastAPI documentation
  to see what the right fix is. After I installed the ML dependencies on my
  laptop, `httpx2` was installed too (as a dependency of `huggingface-hub`) and
  the warning no longer appeared in my local runs. In CI it still appears. I do
  not yet know if that is the real fix or only a side effect.
- **How I will check it:** read the Starlette and FastAPI release notes, then
  decide whether to add `httpx2` to `requirements-dev.txt`.
- **Time spent:** not tracked

## 2026-10-23: Week 2 status, and what is still open

- **Task given to the assistant:** guide me step by step through tasks 9 to 13 and
  tell me which commands to run.
- **Result:** done and merged, each in a small pull request with CI green: database
  schema and Alembic migration, tenant authentication (JWT and API key), tenant
  isolation tests that also run on Postgres in CI, `POST /reviews/analyze` with a
  public IndoBERT sentiment model (`mdhugol/indonesia-bert-sentiment-classification`),
  and structured JSON logging with a request id. The last CI run on Postgres had
  47 tests passed, 0 skipped, coverage 98.47%.
- **What is not done or not proven:**
  - I only tried the real model on 3 example sentences. That shows it loads and
    that the labels are mapped correctly. It is not a measure of accuracy. F1 will
    be measured later on labeled reviews.
  - The model was not trained on skincare reviews, and its model card gives no
    license or accuracy numbers.
  - The results of `/reviews/analyze` are not stored in the database yet.
  - The `tenant_id` is not in the log lines yet.
  - The tests of the other files still use SQLite. Only the isolation tests run on
    Postgres.
  - There is no login endpoint yet, so tokens cannot be issued by the API.
  - The deprecation warning above is not resolved.
  - The `conftest.py` that blocks the real model in tests was missing until
    2026-10-29 (see the entry above).
- **How I checked it:** CI results above, the real model run on my laptop, and
  one real JSON log line from the running server.
- **Time spent:** not tracked
