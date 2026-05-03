from dataclasses import asdict, dataclass, fields

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

    @classmethod
    def from_dict(cls, data: dict) -> 'Schedule':
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        if 'algorithm' in filtered and isinstance(filtered['algorithm'], dict):
            filtered['algorithm'] = Algorithm.from_dict(filtered['algorithm'])
        if 'portfolio' in filtered and isinstance(filtered['portfolio'], dict):
            filtered['portfolio'] = Portfolio.from_dict(filtered['portfolio'])
        for key in known:
            if key not in filtered:
                filtered[key] = None
        for k, v in filtered.items():
            if isinstance(v, str) and v.lower() == 'null':
                filtered[k] = None
        for k, v in filtered.items():
            if isinstance(v, str) and v.lower() == 'null':
                filtered[k] = None
        return cls(**filtered)

    def to_dict(self) -> dict:
        """Convert Schedule instance to a dictionary for JSON serialization."""
        result = asdict(self)
        # Ensure nested objects are properly serialized
        if 'algorithm' in result and isinstance(result['algorithm'], Algorithm):
            result['algorithm'] = result['algorithm'].to_dict()
        if 'portfolio' in result and isinstance(result['portfolio'], Portfolio):
            result['portfolio'] = result['portfolio'].to_dict()
        return result
