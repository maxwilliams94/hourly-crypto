from dataclasses import dataclass

@dataclass
class Algorithm:
    name: str
    description: str
    algo_type: str
    buy_threshold: float
    sell_threshold: float
    sell_below_cost_basis: bool
    buy_percentage: float
    sell_percentage: float
    min_buy_value: float
    min_sell_value: float
    fixed_buy_value: float
    fixed_sell_value: float
    minimum_profit_percentage: float


