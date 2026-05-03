from __future__ import annotations
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Default trading fee rates (as a fraction) charged in fiat on every trade.
# Fees are deducted from the quote (fiat) balance for both buys and sells.
EXCHANGE_FEE_RATES: Dict[str, float] = {
    "coinbase": 0.0075,  # 0.75%
}


@dataclass
class Portfolio:
    asset: str
    quote: str
    exchange: str
    initial_asset_amount: float
    initial_cost_basis: float
    trades: List[Trade]
    current_cost_basis: float
    current_asset_amount: float
    current_quote_amount: float
    cost_basis_value: float
    market_value: float
    last_updated: str
    # Initial quote allocation (fiat budget pre-allocated for buying)
    initial_quote_amount: float = 0.0
    # Current market price per unit (set when price is fetched)
    current_price: float = 0.0

    @classmethod
    def from_dict(cls, data: dict) -> 'Portfolio':
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        if 'trades' in filtered and isinstance(filtered['trades'], list):
            filtered['trades'] = [Trade.from_dict(t) if isinstance(t, dict) else t for t in filtered['trades']]
        for k, v in list(filtered.items()):
            if isinstance(v, str) and v.lower() == 'null':
                filtered[k] = None
        if filtered.get('initial_quote_amount') is None:
            filtered['initial_quote_amount'] = 0.0
        return cls(**filtered)

    def to_dict(self) -> dict:
        """Convert Portfolio instance to a dictionary for JSON serialization."""
        result = asdict(self)
        # Ensure trades are properly serialized
        if 'trades' in result and result['trades']:
            result['trades'] = [t.to_dict() if isinstance(t, Trade) else t for t in result['trades']]
        return result

@dataclass
class Trade:
    id: str
    exchange_id: str
    asset: str
    quote: str
    amount: float
    price: float
    direction: str
    exchange: str
    timestamp: str
    status: str
    last_updated: str
    # Fee paid in fiat for this trade. If None, a default rate is used.
    fee: Optional[float] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'Trade':
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        for key in known:
            if key not in filtered:
                filtered[key] = None
        for k, v in filtered.items():
            if isinstance(v, str) and v.lower() == 'null':
                filtered[k] = None
        return cls(**filtered)

    def is_complete(self):
        return self.status in ["filled", "cancelled", "rejected"]

    def is_filled(self):
        return self.status == "filled"

    def to_dict(self) -> dict:
        """Convert Trade instance to a dictionary for JSON serialization."""
        return asdict(self)


def _parse_iso_utc(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def update_portfolio_trades(portfolio: Portfolio) -> bool:
    """
    Recalculate portfolio cost basis and amounts from initial values and all
    filled trades, using the average cost method.

    Skips the update when no filled trade has occurred since the portfolio was
    last updated (i.e. ``portfolio.last_updated``).

    Returns True if the portfolio was updated, False if it was skipped.
    """
    if portfolio is None:
        return False

    filled_trades = [t for t in (portfolio.trades or []) if t.is_filled()]
    
    # If there are no filled trades at all, nothing to update
    if not filled_trades:
        return False

    # Determine whether there is anything new to process
    if portfolio.last_updated is not None:
        last_updated_dt = _parse_iso_utc(portfolio.last_updated)
        new_filled = [
            t for t in filled_trades
            if t.last_updated is not None
            and _parse_iso_utc(t.last_updated) > last_updated_dt
        ]
        if not new_filled:
            return False

    # Accumulate from initial holdings
    total_amount: float = portfolio.initial_asset_amount or 0.0
    total_cost: float = total_amount * (portfolio.initial_cost_basis or 0.0)
    current_quote: float = portfolio.initial_quote_amount or 0.0

    # Process filled trades in chronological order
    for trade in sorted(filled_trades, key=lambda t: t.timestamp or ""):
        trade_amount: float = trade.amount or 0.0
        trade_price: float = trade.price or 0.0
        trade_cost: float = trade_amount * trade_price

        # Fee is always paid in fiat. Use the recorded fee when available,
        # otherwise fall back to the exchange's default rate.
        if trade.fee is not None:
            fee: float = trade.fee
        else:
            fee_rate = EXCHANGE_FEE_RATES.get((trade.exchange or "").lower(), 0.0)
            fee = trade_cost * fee_rate

        if trade.direction == "buy":
            total_cost += trade_cost
            total_amount += trade_amount
            current_quote -= trade_cost + fee
        elif trade.direction == "sell":
            # Average-cost method: cost basis per unit is unchanged by a sell;
            # only the total cost and position size are reduced.
            current_basis = total_cost / total_amount if total_amount > 0 else 0.0
            total_cost -= current_basis * trade_amount
            total_amount -= trade_amount
            current_quote += trade_cost - fee

    portfolio.current_asset_amount = total_amount
    portfolio.current_cost_basis = total_cost / total_amount if total_amount > 0 else 0.0
    portfolio.current_quote_amount = current_quote
    portfolio.last_updated = datetime.now(timezone.utc).isoformat()

    return True


def update_portfolio_value(portfolio: Portfolio, current_price: float) -> None:
    """
    Update portfolio with current market price and recalculate portfolio values.
    
    Sets:
    - current_price: The current market price per unit
    - cost_basis_value: Total cost basis value (current_asset_amount * current_cost_basis)
    - market_value: Current market value (current_asset_amount * current_price)
    
    Args:
        portfolio: Portfolio instance to update
        current_price: Current market price per unit
    """
    if portfolio is None or current_price is None:
        return
    
    portfolio.current_price = current_price
    portfolio.cost_basis_value = portfolio.current_asset_amount * portfolio.current_cost_basis
    portfolio.market_value = portfolio.current_asset_amount * current_price
    portfolio.last_updated = datetime.now(timezone.utc).isoformat()