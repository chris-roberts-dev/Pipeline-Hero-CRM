"""
Shared decimal precision constants for money and quantity fields.

Centralised here so the catalog apps don't drift on these values. Importing
from a single source means a future precision change (e.g. moving money to
4 decimal places for some currency) is a single-point edit followed by data
migrations, not a hunt across six apps.

Why a plain module rather than an installed app?
  These are constants. They have no models, no migrations, no AppConfig. An
  app would be ceremony around four numbers. If shared *choices* (like UoM
  enums for cross-app reuse) need a home later, that's a separate decision —
  this module is deliberately scoped to numeric precision only.

Money precision:
  12 digits, 2 decimal places. Supports up to $9,999,999,999.99 — well past
  any realistic v1 catalog or quote value. 2 decimals is currency-standard.

Quantity precision:
  14 digits, 4 decimal places. Supports very small fractional quantities
  (e.g. 0.0001 KG of a chemical additive) up to 9,999,999,999.9999 of a
  unit. Distinct from money precision because quantity isn't currency.
"""

MONEY_MAX_DIGITS = 12
MONEY_DECIMAL_PLACES = 2

QUANTITY_MAX_DIGITS = 14
QUANTITY_DECIMAL_PLACES = 4
