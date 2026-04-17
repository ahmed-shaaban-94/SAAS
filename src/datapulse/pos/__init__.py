"""Point-of-Sale module for the DataPulse pharmaceutical platform.

Handles terminal sessions, drug scanning, cart management, checkout
(cash/card/insurance/split), receipt generation, returns, controlled
substance verification, and shift reconciliation.

All POS transactions feed into the analytics pipeline:
  bronze.pos_transactions -> stg_pos_sales -> stg_sales_unified -> fct_sales
"""
