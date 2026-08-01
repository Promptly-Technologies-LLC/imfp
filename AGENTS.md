# AGENTS.md

## Cursor Cloud specific instructions

`imfp` is a pure Python client library (no server, database, or GUI) for downloading
economic data from the IMF SDMX 3.0 JSON API (`https://api.imf.org/external/sdmx/3.0/`).
Dependencies are managed with [uv](https://astral.sh/uv) (`pyproject.toml` + `uv.lock`);
the update script runs `uv sync`, which creates/refreshes the `.venv`.

Run everything through `uv run` (do not activate the venv manually). Key commands:

- Tests: `uv run pytest tests` — fully offline. `tests/conftest.py` mocks HTTP by hashing
  request URLs (SHA256) and replaying cached JSON from `tests/responses/`, so no network
  or API key is needed.
- Format check: `uv run black --check .` (CI's `format.yml` auto-formats on push via
  action-black, so a local reformat finding is expected, not a setup failure).
- Type check: `uv run mypy imfp` (config in `mypy.ini`).
- Build: `uv build` (wheel + sdist into `dist/`).
- Live smoke test / real usage: `uv run python -c "import imfp; print(len(imfp.imf_databases()))"`.

Notes:

- Live calls (`imf_databases()`, `imf_parameters()`, `imf_dataset()`) hit the public IMF API
  and require outbound network; `imf_dataset()` for a large database can take ~30-60s because
  of built-in rate limiting (default 1.5s between requests, tunable via `IMF_WAIT_TIME`).
- Optional env vars (see `imfp/admin.py`): `IMF_APP_NAME` (custom request header to reduce
  rate-limiting) and `IMF_WAIT_TIME`. Neither is required for tests.
- Documentation is built with the external Quarto CLI (`uv run quarto render`, per CI
  `test.yml`). Quarto is not installed by the update script; install it only if editing docs.
