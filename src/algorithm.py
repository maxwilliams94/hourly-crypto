from dataclasses import dataclass, fields

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

    @classmethod
    def from_dict(cls, data: dict) -> 'Algorithm':
        known = {f.name for f in fields(cls)}
        for key in known:
            if key not in filtered:
                filtered[key] = None
        for k, v in filtered.items():
            if isinstance(v, str) and v.lower() == 'null':
                filtered[k] = None
        return cls(**{k: v for k, v in data.items() if k in known})


