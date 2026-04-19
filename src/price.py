from dataclasses import dataclass

@dataclass
class Price:
    asset: str
    quote: str
    exchange: str
    price: float
    schedule: str
    timestamp: str
    active: bool
