"""
Unit tests for create_order() in decision.py.
"""

import pytest
from unittest.mock import MagicMock

from algorithm import Algorithm
from portfolio import Portfolio, Trade
from schedule import Schedule
from order import Order
from decision import create_order


def make_algorithm(**overrides) -> Algorithm:
    defaults = dict(
        name="oracle-algo",
        description="Test oracle algorithm",
        algo_type="oracle",
        buy_threshold=1.0,
        sell_threshold=-1.0,
        sell_below_cost_basis=False,
        buy_percentage=0.10,
        sell_percentage=0.10,
        min_buy_value=10.0,
        min_sell_value=10.0,
        fixed_buy_value=0.0,
        fixed_sell_value=0.0,
        minimum_profit_percentage=0.0,
    )
    defaults.update(overrides)
    return Algorithm(**defaults)


def make_portfolio(**overrides) -> Portfolio:
    defaults = dict(
        asset="BTC",
        quote="USD",
        exchange="test",
        initial_asset_amount=0.0,
        initial_cost_basis=0.0,
        trades=[],
        current_cost_basis=40000.0,
        current_asset_amount=0.1,
        current_quote_amount=1000.0,
        current_net_worth=5000.0,
        last_updated="2024-01-01T00:00:00",
    )
    defaults.update(overrides)
    return Portfolio(**defaults)


def make_schedule(**overrides) -> Schedule:
    defaults = dict(
        id="sched-1",
        asset="BTC",
        quote="USD",
        schedule="1H",
        last_execution=None,
        exchange="test",
        active=True,
        buy_and_sell=True,
        algorithm=make_algorithm(),
        portfolio=make_portfolio(),
    )
    defaults.update(overrides)
    return Schedule(**defaults)


class TestCreateOrderMissingPrices:
    """create_order returns None when price data is unavailable."""

    def test_returns_none_when_current_price_is_none(self):
        schedule = make_schedule()
        result = create_order(schedule, current_price=None, previous_price=50000.0)
        assert result is None

    def test_returns_none_when_previous_price_is_none(self):
        schedule = make_schedule()
        result = create_order(schedule, current_price=51000.0, previous_price=None)
        assert result is None

    def test_returns_none_when_both_prices_are_none(self):
        schedule = make_schedule()
        result = create_order(schedule, current_price=None, previous_price=None)
        assert result is None


class TestCreateOrderBuySignal:
    """Oracle algorithm: price rise above buy_threshold triggers a buy order."""

    def test_buy_order_returned_when_price_rises_above_threshold(self):
        # previous=50000, current=51500 → +3% > buy_threshold of 1%
        schedule = make_schedule()
        order = create_order(schedule, current_price=51500.0, previous_price=50000.0)
        assert order is not None
        assert order.direction == "buy"
        assert order.asset == "BTC"
        assert order.quote == "USD"

    def test_buy_order_price_equals_current_price(self):
        schedule = make_schedule()
        order = create_order(schedule, current_price=51500.0, previous_price=50000.0)
        assert order.price == 51500.0

    def test_no_buy_when_price_change_below_threshold(self):
        # +0.5% is below buy_threshold of 1% → no order
        schedule = make_schedule()
        order = create_order(schedule, current_price=50250.0, previous_price=50000.0)
        assert order is None


class TestCreateOrderSellSignal:
    """Oracle algorithm: price drop below sell_threshold triggers a sell order."""

    def test_sell_order_returned_when_price_drops_below_threshold(self):
        # previous=50000, current=48500 → -3% < sell_threshold of -1%
        schedule = make_schedule()
        order = create_order(schedule, current_price=48500.0, previous_price=50000.0)
        assert order is not None
        assert order.direction == "sell"

    def test_sell_blocked_below_cost_basis_when_flag_false(self):
        # current price (30000) is below cost_basis (40000) and
        # sell_below_cost_basis=False → should return None
        algo = make_algorithm(sell_below_cost_basis=False)
        portfolio = make_portfolio(current_cost_basis=40000.0)
        schedule = make_schedule(algorithm=algo, portfolio=portfolio)
        order = create_order(schedule, current_price=30000.0, previous_price=50000.0)
        assert order is None

    def test_sell_allowed_below_cost_basis_when_flag_true(self):
        algo = make_algorithm(sell_below_cost_basis=True)
        portfolio = make_portfolio(current_cost_basis=40000.0)
        schedule = make_schedule(algorithm=algo, portfolio=portfolio)
        order = create_order(schedule, current_price=30000.0, previous_price=50000.0)
        assert order is not None
        assert order.direction == "sell"

    def test_no_sell_when_price_change_above_threshold(self):
        # -0.5% is above sell_threshold of -1% → no order
        schedule = make_schedule()
        order = create_order(schedule, current_price=49750.0, previous_price=50000.0)
        assert order is None


class TestCreateOrderZeroPreviousPrice:
    """Percentage change is 0 when previous_price is zero – no signal."""

    def test_no_order_when_previous_price_is_zero(self):
        schedule = make_schedule()
        order = create_order(schedule, current_price=50000.0, previous_price=0.0)
        assert order is None
