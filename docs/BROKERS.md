Broker Integrations
===================

Implemented
-----------
- IBKR
  - History: FlexQuery (official statements)
  - Live: TWS/Gateway (positions, quotes, orders)
- TastyTrade
  - SDK with username/password

Planned
-------
- Schwab: OAuth app required. Env: SCHWAB_CLIENT_ID, SCHWAB_CLIENT_SECRET, SCHWAB_REDIRECT_URI. Live trading: Yes after app approval.
- Fidelity: no broad public trading API. Possible via partner/experimental; likely read-only first.
- Robinhood: private/undocumented API; trading possible but stability/ToS concerns. Prefer read-only.

Approach to add a broker
------------------------
1) Create client in backend/services/clients/<broker>_client.py
2) Normalize data to our models
3) Add sync service under backend/services/portfolio/
4) Add routes for account add/sync
5) Update seeding to discover accounts from credentials if possible

