import logging
from dataclasses import dataclass, fields
from typing import List, Tuple

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

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate that all required fields for the algorithm type are set.

        Returns:
            (is_valid, errors) — errors is empty when is_valid is True.
        """
        errors: List[str] = []

        # Common required fields
        if not self.algo_type:
            errors.append("algo_type is not set")
        if self.buy_threshold is None:
            errors.append("buy_threshold is not set")
        if self.sell_threshold is None:
            errors.append("sell_threshold is not set")
        if self.sell_below_cost_basis is None:
            errors.append("sell_below_cost_basis is not set")

        if self.algo_type == "oracle":
            if not self.buy_percentage:
                errors.append("oracle: buy_percentage is not set or zero")
            if not self.sell_percentage:
                errors.append("oracle: sell_percentage is not set or zero")
            if not self.min_buy_value:
                errors.append("oracle: min_buy_value is not set or zero")
            if not self.min_sell_value:
                errors.append("oracle: min_sell_value is not set or zero")
        elif self.algo_type == "arbitrage":
            if not self.fixed_buy_value:
                errors.append("arbitrage: fixed_buy_value is not set or zero")
            if not self.fixed_sell_value:
                errors.append("arbitrage: fixed_sell_value is not set or zero")
        elif self.algo_type:
            errors.append(f"unknown algo_type: '{self.algo_type}'")

        if errors:
            for error in errors:
                logging.error(f"Algorithm '{self.name}' validation error: {error}")
            return False, errors

        return True, []

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


