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
