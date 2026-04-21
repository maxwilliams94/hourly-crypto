from __future__ import annotations
from dataclasses import dataclass, fields
from typing import List

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
    current_net_worth: float
    last_updated: str

    @classmethod
    def from_dict(cls, data: dict) -> 'Portfolio':
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        if 'trades' in filtered and isinstance(filtered['trades'], list):
            filtered['trades'] = [Trade.from_dict(t) if isinstance(t, dict) else t for t in filtered['trades']]
        return cls(**filtered)

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