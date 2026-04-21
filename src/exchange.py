import datetime
import logging
from os import environ
from typing import Tuple, Dict, Any
from uuid import uuid4

from order import Order
from portfolio import Trade
from price import Price

from exchanges.coinbase import get_current_price as cb_get_current_price
from exchanges.coinbase import get_order_status as cb_get_order_status
from exchanges.coinbase import place_order as cb_place_order
from exchanges.coinbase import verify_coinbase_connection as cb_verify_connection

from random import randint

def get_current_price(asset: str, quote: str, exchange: str) -> Price:
    if exchange == "coinbase":
        return cb_get_current_price(asset, quote)
    elif exchange == "test":
        return Price(id=str(uuid4()), asset=asset, quote=quote, exchange=exchange, price=float(randint(1,1000)), schedule=None, timestamp=datetime.datetime.now().isoformat(), active=True)
    else:
        logging.warning(f"Unknown exchange '{exchange}' for price retrieval. Returning None.")
        return None


def get_trade_status(trade: Trade) -> Tuple[bool, Trade]:
    """
    Get the status of an trade. Uses the exchange id
    
    Args:
        trade
        exchange: The exchange name (e.g., "coinbase")
        
    """
    if trade.exchange == "coinbase":
        status = cb_get_order_status(trade.exchange_id)
    elif trade.exchange == "test":
        status = "filled"
    else:
        status = None

    changed = status != trade.status
    trade.status = status
    trade.last_updated = datetime.datetime.now().isoformat()
    return changed, trade


def execute_order(order: Order) -> Trade:
    if not order.execution_active or dry_trading():
        logging.info(f"Dry trading enabled or order not active for execution. Simulating trade execution for order: {order}")
        return Trade(
            id=str(uuid4()),
            exchange_id="simulated",
            asset=order.asset,
            quote=order.quote,
            exchange=order.exchange,
            amount=order.base_amount,
            price=order.price,
            direction=order.direction,
            timestamp=datetime.datetime.now().isoformat(),
            status="pending",
            last_updated=datetime.datetime.now().isoformat()
        )
    if order.exchange == "coinbase":
        return cb_place_order(order)
    elif order.exchange == "test":
        return Trade(
            id=str(uuid4()),
            exchange_id="test-id",
            asset=order.asset,
            quote=order.quote,
            exchange=order.exchange,
            amount=order.base_amount,
            price=order.price,
            direction=order.direction,
            timestamp=datetime.datetime.now().isoformat(),
            status="pending",
            last_updated=datetime.datetime.now().isoformat()
        )
    else:
        return None
    

def check_exchange_connectivity(exchange: str) -> bool:
    if (exchange == "coinbase"):
        return len(cb_verify_connection()) > 0
    elif exchange == "test":
        return True
    else:
        return False
        

def dry_trading() -> bool:
    return environ.get("DRY", "true").lower() == "true"
