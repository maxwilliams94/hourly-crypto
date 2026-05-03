"""
Unit tests for exchange.py.

All external integrations (Coinbase SDK, environment variables) are mocked.
"""

import datetime
import pytest
from unittest.mock import patch, MagicMock

from order import Order
from portfolio import Trade, Portfolio, update_portfolio_trades
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

    def test_test_exchange_calculates_1_percent_fee_on_fill(self):
        """When test exchange transitions to filled, apply 1% fee."""
        # 0.01 BTC @ 50,000 = $500 trade cost
        # 1% fee = $5
        trade = make_trade(exchange="test", status="open", amount=0.01, price=50000.0, fee=None)
        changed, updated = exchange_module.update_trade(trade)
        assert updated.status == "filled"
        expected_fee = 0.01 * 50000.0 * 0.01  # amount * price * 1%
        assert updated.fee == pytest.approx(expected_fee)
        assert changed is True

    def test_test_exchange_preserves_explicit_fee(self):
        """If fee is already set, don't recalculate for test exchange."""
        trade = make_trade(exchange="test", status="open", amount=0.01, price=50000.0, fee=10.0)
        changed, updated = exchange_module.update_trade(trade)
        assert updated.status == "filled"
        assert updated.fee == 10.0  # Preserve explicit fee
        # Changed because status changed (fee didn't)
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
        # For test exchange on first fill, fee is calculated as 1%
        expected_fee = trade.amount * trade.price * 0.01
        assert updated.fee == pytest.approx(expected_fee)


# ---------------------------------------------------------------------------
# Integration: update_trade + portfolio update
# ---------------------------------------------------------------------------

class TestExchangePortfolioIntegration:
    """Verify that exchange fees flow correctly into portfolio updates."""

    def test_test_exchange_fill_fee_flows_to_portfolio(self):
        """
        Test exchange buy: 1 BTC @ 40,000
        - Trade cost: 40,000
        - Fee (1%): 400
        - Total fiat deducted: 40,400
        
        Portfolio should reflect: 1 BTC at 40,000 cost basis, quote reduced by 40,400
        """
        # Start with pending trade (no fee yet)
        pending_trade = Trade(
            id="t1",
            exchange_id="test-1",
            asset="BTC",
            quote="USD",
            amount=1.0,
            price=40000.0,
            direction="buy",
            exchange="test",
            timestamp="2024-01-01T00:00:00",
            status="pending",
            last_updated="2024-01-01T00:00:00",
            fee=None,
        )
        
        # Update trade to filled (should calculate 1% fee)
        changed, filled_trade = exchange_module.update_trade(pending_trade)
        assert changed is True
        assert filled_trade.status == "filled"
        assert filled_trade.fee == pytest.approx(400.0)  # 1% of 40,000
        
        # Create portfolio with this filled trade
        portfolio = Portfolio(
            asset="BTC",
            quote="USD",
            exchange="test",
            initial_asset_amount=0.0,
            initial_cost_basis=0.0,
            initial_quote_amount=50000.0,  # $50k starting budget
            trades=[filled_trade],
            current_cost_basis=0.0,
            current_asset_amount=0.0,
            current_quote_amount=50000.0,
            cost_basis_value=0.0,
            market_value=0.0,
            last_updated=None,
        )
        
        # Update portfolio with the filled trade
        updated = update_portfolio_trades(portfolio)
        assert updated is True
        
        # Verify portfolio state: 1 BTC cost basis 40k, quote reduced by 40k + 400 fee
        assert portfolio.current_asset_amount == pytest.approx(1.0)
        assert portfolio.current_cost_basis == pytest.approx(40000.0)
        assert portfolio.current_quote_amount == pytest.approx(50000.0 - 40000.0 - 400.0)  # 9,600

    def test_test_exchange_multiple_fills_with_fees(self):
        """
        Verify multiple test exchange fills each with 1% fee.
        Buy 1 BTC @ 40k (fee: 400) → Buy 0.5 BTC @ 50k (fee: 250)
        """
        t1 = Trade(
            id="t1", exchange_id="test-1", asset="BTC", quote="USD",
            amount=1.0, price=40000.0, direction="buy", exchange="test",
            timestamp="2024-01-01T10:00:00", status="filled", 
            last_updated="2024-01-01T10:00:00", fee=400.0,
        )
        t2 = Trade(
            id="t2", exchange_id="test-2", asset="BTC", quote="USD",
            amount=0.5, price=50000.0, direction="buy", exchange="test",
            timestamp="2024-01-01T11:00:00", status="pending",
            last_updated="2024-01-01T11:00:00", fee=None,
        )
        
        # Update t2 to filled
        _, filled_t2 = exchange_module.update_trade(t2)
        assert filled_t2.fee == pytest.approx(250.0)  # 1% of 25,000
        
        # Portfolio with both trades
        portfolio = Portfolio(
            asset="BTC", quote="USD", exchange="test",
            initial_asset_amount=0.0, initial_cost_basis=0.0,
            initial_quote_amount=100000.0,
            trades=[t1, filled_t2],
            current_cost_basis=0.0, current_asset_amount=0.0,
            current_quote_amount=100000.0,
            cost_basis_value=0.0, market_value=0.0, last_updated=None,
        )
        
        update_portfolio_trades(portfolio)
        
        # Verify: 1.5 BTC, avg cost = (40000 + 25000) / 1.5 ≈ 43,333.33
        # Quote: 100k - 40k - 400 - 25k - 250 = 34,350
        assert portfolio.current_asset_amount == pytest.approx(1.5)
        expected_avg_cost = (40000.0 + 25000.0) / 1.5
        assert portfolio.current_cost_basis == pytest.approx(expected_avg_cost)
        assert portfolio.current_quote_amount == pytest.approx(100000.0 - 40000.0 - 400.0 - 25000.0 - 250.0)
