from dataclasses import dataclass

from algorithm import Algorithm
from portfolio import Portfolio


@dataclass
class Schedule:
    id: str
    asset: str
    quote: str
    schedule: str
    last_execution: str
    exchange: str
    active: bool
    buy_and_sell: bool

    algorithm: Algorithm
    portfolio: Portfolio
