Models Reference
================

Core
----
- BrokerAccount
  - Fields: user_id, broker, account_number, account_name, account_type, status, sync_status, last_successful_sync
  - Notes: Single source for accounts across brokers

- Position (stocks/equities)
  - Purpose: a user's stock position in a specific broker account
  - Key: (user_id, account_id, symbol)
  - Fields: quantity, average_cost, total_cost_basis, current_price, market_value, unrealized_pnl, unrealized_pnl_pct, day_pnl, sector, industry
  - API DTO (stocks rows):
    - symbol, position (quantity), average_cost, market_price, position_value, unrealized_pnl, unrealized_pnl_pct, day_change, day_change_pct, sector

- Option (options contract/position)
  - Unique: (account_id, underlying_symbol, strike_price, expiry_date, option_type)
  - Fields: open_quantity, current_price, market_value, unrealized_pnl, multiplier, data_source
  - API DTO (options rows):
    - symbol/underlying_symbol, strike_price, expiration_date, option_type, quantity (contracts), average_open_price, current_price, market_value, unrealized_pnl, days_to_expiration, multiplier

- Trade
  - Unique: (account_id, execution_id) and (account_id, order_id)
  - Fields: symbol, side, quantity, price, executed_at, commission, exchange, contract_type

- Transaction
  - Unique: (account_id, external_id) and (account_id, execution_id)
  - Fields: symbol, description, transaction_type, quantity, trade_price, amount, currency, transaction_date

- TaxLot
  - Fields: acquisition_date, quantity, cost_per_share, current_price, unrealized_pnl, is_long_term
  - Methods: FIFO/LIFO/HIFO support in service layer

- AccountBalance
  - Fields: balance_date, net_liquidation, cash, buying_power, margin requirements

- Signals/Alerts
  - ATR signals, portfolio alerts; Discord notifications

Constraints and Integrity
- Enforced uniqueness on trades, transactions, and options to prevent brokerage dupes
- Foreign keys point to `BrokerAccount`
- Use enums from `backend/models/broker_account.py` and related enums for consistency

Naming conventions (reduce confusion)
-------------------------------------
- Use "stocks" and "options" in routes/pages; avoid the term "holdings".
- Use "position" to refer to a position row (stock or option). For stocks: `Position`. For options: `Option`.
- Align DTO field names across API responses:
  - For stocks, prefer: position (quantity), average_cost, market_price, position_value, day_change.
  - For options, prefer: quantity (contracts), average_open_price, current_price, market_value.

Testing Checklist per Model
--------------------------
- Creation and basic persistence
- Uniqueness constraint violations (expected failure)
- Relationship integrity (FKs)
- Serialization shape used by API routes

