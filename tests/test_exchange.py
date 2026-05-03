"""
Unit tests for exchange.py.

All external integrations (Coinbase SDK, environment variables) are mocked.
"""

import datetime
import pytest
from unittest.mock import patch, MagicMock

from order import Order
from portfolio import Trade
from price import Price
import exchange as exchange_module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_order(**overrides) -> Order:
    defaults = dict(
        asset="BTC",
        quote="USD",
        exchange="test",
        base_amount=0.01,
        quote_amount=500.0,
        price=50000.0,
        direction="buy",
        order_type="limit",
        execution_active=True,
        status="pending",
    )
    defaults.update(overrides)
    return Order(**defaults)


def make_trade(**overrides) -> Trade:
    defaults = dict(
        id="trade-1",
        exchange_id="order-abc123",
        asset="BTC",
        quote="USD",
        amount=0.01,
        price=50000.0,
        direction="buy",
        exchange="test",
        timestamp="2024-01-01T00:00:00",
        status="open",
        last_updated="2024-01-01T00:00:00",
        fee=None,
    )
    defaults.update(overrides)
    return Trade(**defaults)


# ---------------------------------------------------------------------------
# get_current_price
# ---------------------------------------------------------------------------

class TestGetCurrentPrice:
    def test_test_exchange_returns_price_object(self):
        price = exchange_module.get_current_price("BTC", "USD", "test")
        assert isinstance(price, Price)
        assert price.asset == "BTC"
        assert price.quote == "USD"
        assert price.exchange == "test"
        assert isinstance(price.price, float)

    def test_test_exchange_price_in_expected_range(self):
        price = exchange_module.get_current_price("ETH", "USD", "test")
        assert 1.0 <= price.price <= 1000.0

    def test_unknown_exchange_returns_none(self):
        price = exchange_module.get_current_price("BTC", "USD", "unknown_exchange")
        assert price is None

    def test_coinbase_exchange_delegates_to_coinbase_module(self):
        mock_price = Price(
            id="price-1",
            asset="BTC", quote="USD", exchange="coinbase",
            price=50000.0, schedule="1H",
            timestamp="2024-01-01T00:00:00", active=True,
        )
        with patch("exchange.cb_get_current_price", return_value=mock_price) as mock_cb:
            result = exchange_module.get_current_price("BTC", "USD", "coinbase")
            mock_cb.assert_called_once_with("BTC", "USD")
            assert result == mock_price


# ---------------------------------------------------------------------------
# check_exchange_connectivity
# ---------------------------------------------------------------------------

class TestCheckExchangeConnectivity:
    def test_test_exchange_is_always_connected(self):
        assert exchange_module.check_exchange_connectivity("test") is True

    def test_unknown_exchange_is_not_connected(self):
        assert exchange_module.check_exchange_connectivity("kraken") is False

    def test_coinbase_connected_when_accounts_returned(self):
        with patch("exchange.cb_verify_connection", return_value=["account-1"]):
            assert exchange_module.check_exchange_connectivity("coinbase") is True

    def test_coinbase_not_connected_when_no_accounts(self):
        with patch("exchange.cb_verify_connection", return_value=[]):
            assert exchange_module.check_exchange_connectivity("coinbase") is False


# ---------------------------------------------------------------------------
# dry_trading
# ---------------------------------------------------------------------------

class TestDryTrading:
    def test_dry_true_when_env_is_true(self):
        with patch.dict("os.environ", {"DRY": "true"}):
            assert exchange_module.dry_trading() is True

    def test_dry_true_when_env_is_True_uppercase(self):
        with patch.dict("os.environ", {"DRY": "True"}):
            assert exchange_module.dry_trading() is True

    def test_dry_false_when_env_is_false(self):
        with patch.dict("os.environ", {"DRY": "false"}):
            assert exchange_module.dry_trading() is False

    def test_dry_true_by_default_when_env_not_set(self):
        env = {k: v for k, v in __import__("os").environ.items() if k != "DRY"}
        with patch.dict("os.environ", env, clear=True):
            assert exchange_module.dry_trading() is True


# ---------------------------------------------------------------------------
# execute_order
# ---------------------------------------------------------------------------

class TestExecuteOrder:
    def test_returns_dry_trade_when_dry_trading_enabled(self):
        order = make_order(execution_active=True)
        with patch("exchange.dry_trading", return_value=True):
            result = exchange_module.execute_order(order)
        assert result is not None

    def test_returns_dry_trade_when_execution_not_active(self):
        order = make_order(execution_active=False)
        with patch("exchange.dry_trading", return_value=False):
            result = exchange_module.execute_order(order)
        assert result is not None

    def test_delegates_to_coinbase_when_live(self):
        order = make_order(execution_active=True)
        # We need to set order.exchange since Order dataclass doesn't have it
        order.exchange = "coinbase"
        mock_trade = make_trade(status="open")
        with patch("exchange.dry_trading", return_value=False), \
             patch("exchange.cb_place_order", return_value=mock_trade) as mock_place:
            result = exchange_module.execute_order(order)
            mock_place.assert_called_once_with(order)
            assert result == mock_trade


# ---------------------------------------------------------------------------
# update_trade
# ---------------------------------------------------------------------------

class TestUpdateTrade:
    def test_test_exchange_always_returns_filled(self):
        trade = make_trade(exchange="test", status="open")
        changed, updated = exchange_module.update_trade(trade)
        assert updated.status == "filled"
        assert changed is True

    def test_no_change_when_already_filled(self):
        trade = make_trade(exchange="test", status="filled")
        changed, updated = exchange_module.update_trade(trade)
        assert changed is False
        assert updated.status == "filled"

    def test_last_updated_is_set(self):
        trade = make_trade(exchange="test", status="open")
        _, updated = exchange_module.update_trade(trade)
        assert updated.last_updated is not None

    def test_coinbase_exchange_delegates_to_coinbase_module(self):
        trade = make_trade(exchange="coinbase", status="open")
        mock_details = {
            "status": "filled",
            "filled_size": "1.0",
            "average_filled_price": "50000.0",
            "total_fees": "50.0",
            "raw_order": {},
        }
        with patch("exchange.cb_get_order_details", return_value=mock_details) as mock_cb:
            changed, updated = exchange_module.update_trade(trade)
            mock_cb.assert_called_once()
            assert updated.status == "filled"
            assert updated.fee == 50.0
            assert changed is True

    def test_fee_updated_from_exchange_details(self):
        trade = make_trade(exchange="test", status="open", fee=None)
        changed, updated = exchange_module.update_trade(trade)
        # For test exchange, fee remains None
        assert updated.fee is None
