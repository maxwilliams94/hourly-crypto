from dataclasses import dataclass

@dataclass
class Order:
    asset: str
    quote: str
    exchange: str
    base_amount: float
    quote_amount: float
    price: float
    direction: str
    order_type: str
    execution_active: bool
    status: str
