Status
======

Today
-----
- RBAC added: JWT role claim; `/api/v1/auth/me` returns role; admin guard via `require_roles`; admin routes under `/api/v1/admin/*`.
- Test DB isolation: `TEST_DATABASE_URL` required; Alembic upgrades to head on test engine; per-test transaction rollback.
- Migration CLI: `./run.sh migrate | makemigration \"msg\" | downgrade <rev> | stamp`.
- Dev proxy enabled: frontend uses relative `/api/v1` with Vite proxy to backend (no CORS in dev).
- Aggregator connects (TT/IBKR) are async (job_id + status polling); TT MFA supported.
- Docker: `./run.sh start` now brings up frontend automatically; `./run.sh status` shows frontend URL.

Next
----
- Provide exact Schwab Authorization Endpoint and set `SCHWAB_AUTH_BASE` to resolve 404/502.
- Confirm admin seed via `.env` (`ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`) and verify `/api/v1/admin/system/status`.
- Continue wizard UX polish and ensure modal closes immediately on TT/IBKR success.

