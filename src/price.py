from dataclasses import dataclass, fields

@dataclass
class Price:
    id: str
    asset: str
    quote: str
    exchange: str
    price: float
    schedule: str
    timestamp: str
    active: bool

    @classmethod
    def from_dict(cls, data: dict) -> 'Price':
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        for key in known:
            if key not in filtered:
                filtered[key] = None
        for k, v in filtered.items():
            if isinstance(v, str) and v.lower() == 'null':
                filtered[k] = None
        return cls(**filtered)

    def __sub__(self, other):
        if not isinstance(other, Price):
            return NotImplemented
        if self.asset != other.asset or self.quote != other.quote:
            raise ValueError("Cannot compare prices with different asset/quote/exchange")
        return self.price - other.price
