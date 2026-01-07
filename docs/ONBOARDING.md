Onboarding (Humans + Agents)
===========================

This repo is a Docker-first monorepo.

- Backend: FastAPI + SQLAlchemy + Alembic
- Frontend: React + Vite + Chakra UI
- State: Postgres + Redis

Golden rules
------------

1) **Never run tests against the dev database.**
   - Backend tests are designed to **fail closed** if `TEST_DATABASE_URL` is missing or unsafe.
   - The only supported backend test entrypoint is `./run.sh test` (or `make test`).

2) **No direct pushes to `main`.**
   - Dependabot PRs may auto-merge after CI passes.
   - Everything else lands via PR.

3) **Infra is canonical under `infra/`.**
   - Dev stack: `infra/compose.dev.yaml` + `infra/env.dev`
   - Test stack: `infra/compose.test.yaml` + `infra/env.test`

Prerequisites
-------------
- Docker Desktop
- `make`
- Node is only needed on host if you run the frontend outside Docker (not recommended).

Quick start (dev stack)
-----------------------
- `./run.sh start`
- `./run.sh status`
- `./run.sh logs`

Run tests (safe, isolated DB)
-----------------------------
- `./run.sh test`

Other useful targets:
- Backend only (isolated DB): `make test`
- Frontend unit checks: `make test-frontend`
- Both: `make test-all`

Notes:
- This uses `infra/compose.test.yaml` with `postgres_test` + an isolated Docker volume.
- `infra/env.test` is untracked; if missing, `./run.sh test` copies from `infra/env.test.example`.

Migrations (dev DB only)
------------------------
- Apply migrations:
  - `./run.sh migrate`
- Create an autogenerate migration:
  - `./run.sh makemigration "add new table"`
- Downgrade:
  - `./run.sh downgrade -1`
- Stamp head:
  - `./run.sh stamp`

CI (GitHub Actions)
-------------------
- Workflow: `.github/workflows/ci.yml`
  - Backend: pytest runs in Docker (same isolation as local)
  - Frontend: lint + typecheck + unit tests

PR automation
-------------
See `docs/PR_AUTOMATION.md`.


