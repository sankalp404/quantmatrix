Roadmap
=======

Helpful Commands
----------------
- Start stack: `./run.sh start`
- Restart stack: `./run.sh restart`
- Status: `./run.sh status`
- Logs (backend): `./run.sh logs`
- Tests: `./run.sh test` (runs in isolated Docker test DB; no dev DB access)
- Migrations: `./run.sh migrate`
- Create migration: `./run.sh makemigration "message"`
- Downgrade: `./run.sh downgrade <rev>`
- Stamp head: `./run.sh stamp`

Milestones
----------
1) Data sync (IBKR + TastyTrade) – current
2) Portfolio UI (Snowball Analytics+) – current
3) Historical store for stocks/indices – next
4) Strategies + automation – next
5) Notifications + alerts – next
6) Primo strategy (text → portfolio) – later

Operational
-----------
- CI runs tests, lints, alembic upgrade head
- CHANGELOG generated from conventional commits
- STATUS.md updated on merges

