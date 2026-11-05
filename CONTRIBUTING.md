# Contributing

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Runtime dependencies live in `requirements.txt`; test and lint tooling (pytest, httpx, pytest-cov, ruff, mypy) lives in `requirements-dev.txt`. Python 3.11 or newer is required.

## Before opening a pull request

Run the same checks CI runs:

```bash
ruff check .
mypy
python -m pytest --cov        # fails below 90 % line/branch coverage
```

1. Use fictional data only.
2. Keep domain rules (`app/domain.py`) independent of HTTP handlers; handlers talk to the `IncidentRepository` interface only.
3. Add tests for behavior changes, including the 404/409/422 error paths. Tests get a fresh repository, an empty audit log and a fixed clock from `tests/conftest.py`; use the `clock` fixture instead of real time.
4. Document new API contracts or limitations in the README and add an entry under `Unreleased` in `CHANGELOG.md`.
5. Do not commit secrets, personal information, real incident data, or generated artifacts (`.coverage`, caches, `egg-info`).
6. Write commit messages in the imperative mood and explain the why when it is not obvious.
