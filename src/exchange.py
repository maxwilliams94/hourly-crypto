import datetime
import logging
from dataclasses import replace
from os import environ
from typing import Tuple, Dict, Any
from uuid import uuid4

from order import Order
from portfolio import Trade
from price import Price

from exchanges.coinbase import get_current_price as cb_get_current_price
from exchanges.coinbase import get_order_details as cb_get_order_details
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


def update_trade(trade: Trade) -> Tuple[bool, Trade]:
    """
    Update trade information from the exchange, including status and fees.
    Queries the exchange for current trade details and returns an updated copy
    of the trade with new status and fee information.
    
    Args:
        trade: The Trade object to update
        
    Returns:
        Tuple of (changed, updated_trade) where:
        - changed: bool indicating if status or fee changed
        - updated_trade: New Trade instance with updated status and fee
    """
    if trade.exchange == "coinbase":
        details = cb_get_order_details(trade.exchange_id)
        new_status = details["status"]
        new_fee = details.get("total_fees")
        
        # Parse total_fees to float if it's a string
        if new_fee is not None and isinstance(new_fee, str):
            try:
                new_fee = float(new_fee)
            except (ValueError, TypeError):
                new_fee = None
    elif trade.exchange == "test":
        new_status = "filled"
        new_fee = trade.fee
    else:
        new_status = None
        new_fee = trade.fee

    changed = new_status != trade.status or new_fee != trade.fee
    
    # Return a new Trade instance with updated values
    updated_trade = replace(
        trade,
        status=new_status,
        fee=new_fee,
        last_updated=datetime.datetime.now().isoformat()
    )
    
    return changed, updated_trade


def execute_order(order: Order) -> Trade:
    if not order.execution_active or dry_trading():
        logging.info(f"Dry trading enabled or order not active for execution. Simulating trade execution for order: {order}")
        would_be_trade = Trade(
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
            last_updated=datetime.datetime.now().isoformat(),
            fee=None,
        )
        logging.info("Simulated trade: {}".format(would_be_trade))
        return None
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
            last_updated=datetime.datetime.now().isoformat(),
            fee=None,
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
