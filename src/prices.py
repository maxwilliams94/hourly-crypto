
import logging
from datetime import datetime, timezone, timedelta

from price import Price
from repo import persist_price, get_prices

_SCHEDULE_INTERVALS = {
    "1M": timedelta(minutes=1),
    "1H": timedelta(hours=1),
    "4H": timedelta(hours=4),
    "1D": timedelta(days=1),
    "1W": timedelta(weeks=1),
}


def save_price(price: Price) -> None:
    persist_price(price)


def get_previous_price(asset: str, quote: str, schedule: str, exchange: str) -> Price:
    prices = get_prices(asset, quote, schedule, exchange, 1)
    if len(prices) == 0:
        return None

    price = prices[0]
    if price.timestamp is None:
        logging.warning(
            "Previous price for %s/%s on %s (%s) has no timestamp; rejecting",
            asset, quote, exchange, schedule,
        )
        return None

    interval = _SCHEDULE_INTERVALS.get(schedule)
    if interval is not None:
        now = datetime.now(timezone.utc)
        price_time = datetime.fromisoformat(price.timestamp)
        if price_time.tzinfo is None:
            price_time = price_time.replace(tzinfo=timezone.utc)
        age = now - price_time
        tolerance = interval * 1.1
        if age > tolerance:
            logging.warning(
                "Previous price for %s/%s on %s (%s) is stale: age %s exceeds expected interval %s by more than 10%%",
                asset, quote, exchange, schedule, age, interval,
            )
            return None

    return price
        