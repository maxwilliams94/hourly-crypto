
from .price import Price
from .repo import persist_price, get_prices


def save_price(price: Price) -> None:
    persist_price(price)


def get_previous_price(asset: str, quote: str, schedule: str, exchange: str) -> Price:
    prices = get_prices(asset, quote, schedule, exchange, 1)
    return prices[0] if len(prices) > 0 else None
        