from __future__ import annotations
from dataclasses import dataclass
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

@dataclass
class Trade:
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

    def is_complete(self):
        return self.status in ["filled", "cancelled", "rejected"]

    def is_filled(self):
        return self.status == "filled"