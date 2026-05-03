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


def make_oracle_algorithm(**overrides) -> Algorithm:
    """Create an oracle algorithm with percentage-based buy/sell fields."""
    defaults = dict(
        name="oracle-algo",
        description="Test oracle algorithm",
        algo_type="oracle",
        buy_threshold=1.0,
        sell_threshold=-1.0,
        sell_below_cost_basis=False,
        # Oracle-specific fields: percentage-based with minimum values
        buy_percentage=0.10,  # Buy 10% of current quote amount
        sell_percentage=0.10,  # Sell 10% of current asset amount
        min_buy_value=10.0,  # Minimum quote amount per buy (e.g., $10)
        min_sell_value=10.0,  # Minimum quote amount per sell (e.g., $10)
        # Arbitrage fields (unused in oracle, set to 0)
        fixed_buy_value=0.0,
        fixed_sell_value=0.0,
        minimum_profit_percentage=0.0,
    )
    defaults.update(overrides)
    return Algorithm(**defaults)


def make_arbitrage_algorithm(**overrides) -> Algorithm:
    """Create an arbitrage algorithm with fixed-value buy/sell fields."""
    defaults = dict(
        name="arbitrage-algo",
        description="Test arbitrage algorithm",
        algo_type="arbitrage",
        buy_threshold=1.0,
        sell_threshold=-1.0,
        sell_below_cost_basis=False,
        # Oracle fields (unused in arbitrage, should be 0)
        buy_percentage=0.0,
        sell_percentage=0.0,
        min_buy_value=0.0,
        min_sell_value=0.0,
        # Arbitrage-specific fields: fixed values per trade
        fixed_buy_value=100.0,  # Always buy exactly $100 worth
        fixed_sell_value=100.0,  # Always sell exactly $100 worth
        minimum_profit_percentage=0.0,
    )
    defaults.update(overrides)
    return Algorithm(**defaults)


def make_algorithm(**overrides) -> Algorithm:
    """Generic algorithm factory (defaults to oracle for backward compatibility)."""
    return make_oracle_algorithm(**overrides)


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
        cost_basis_value=4000.0,  # 0.1 * 40000
        market_value=4000.0,      # 0.1 * 40000 (assuming current price = cost basis)
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


class TestOracleAlgorithmBuyOrder:
    """Oracle algorithm: buy order uses buy_percentage and min_buy_value."""

    def test_oracle_buy_uses_percentage_of_portfolio(self):
        """
        Oracle buy: base_amount = (buy_percentage * current_quote_amount) / current_price
        With buy_percentage=0.10, quote_amount=$1000, price=$50,000:
        base_amount = (0.10 * 1000) / 50000 = 0.002 BTC
        """
        algo = make_oracle_algorithm(buy_percentage=0.10)
        portfolio = make_portfolio(current_quote_amount=1000.0)
        schedule = make_schedule(algorithm=algo, portfolio=portfolio)
        
        order = create_order(schedule, current_price=50000.0, previous_price=49500.0)
        assert order is not None
        assert order.direction == "buy"
        
        expected_base = (0.10 * 1000.0) / 50000.0
        assert abs(order.base_amount - expected_base) < 0.0001
        assert abs(order.quote_amount - (order.base_amount * 50000.0)) < 0.01

    def test_oracle_buy_respects_min_buy_value(self):
        """
        When percentage calculation is below min_buy_value, use min_buy_value instead.
        With buy_percentage=0.01 (tiny), quote=$1000, min=$50:
        base_amount = max((0.01 * 1000) / 50000, 50 / 50000) = max(0.0002, 0.001) = 0.001 BTC
        """
        algo = make_oracle_algorithm(
            buy_percentage=0.01,  # Only 1%
            min_buy_value=50.0,   # But at least $50
        )
        portfolio = make_portfolio(current_quote_amount=1000.0)
        schedule = make_schedule(algorithm=algo, portfolio=portfolio)
        
        order = create_order(schedule, current_price=50000.0, previous_price=49500.0)
        assert order is not None
        assert order.direction == "buy"
        
        # Should use min_buy_value
        expected_base = 50.0 / 50000.0
        assert abs(order.base_amount - expected_base) < 0.0001

    def test_oracle_requires_portfolio(self):
        """Oracle algorithm requires a portfolio to calculate percentages."""
        algo = make_oracle_algorithm()
        schedule = make_schedule(algorithm=algo, portfolio=None)
        
        order = create_order(schedule, current_price=50000.0, previous_price=49500.0)
        assert order is None


class TestOracleAlgorithmSellOrder:
    """Oracle algorithm: sell order uses sell_percentage and min_sell_value."""

    def test_oracle_sell_uses_percentage_of_holdings(self):
        """
        Oracle sell: base_amount = sell_percentage * current_asset_amount
        With sell_percentage=0.10, asset_amount=0.1 BTC:
        base_amount = 0.10 * 0.1 = 0.01 BTC
        """
        algo = make_oracle_algorithm(sell_percentage=0.10)
        portfolio = make_portfolio(current_asset_amount=0.1)
        schedule = make_schedule(algorithm=algo, portfolio=portfolio)
        
        order = create_order(schedule, current_price=48500.0, previous_price=50000.0)
        assert order is not None
        assert order.direction == "sell"
        
        expected_base = 0.10 * 0.1
        assert abs(order.base_amount - expected_base) < 0.0001

    def test_oracle_sell_respects_min_sell_value(self):
        """
        When percentage calculation is below min_sell_value, use min_sell_value.
        With sell_percentage=0.01, asset=0.001 BTC, min=$10, price=$50,000:
        - Percentage amount: 0.01 * 0.001 = 0.00001 BTC = $0.50
        - Min sell amount: 10 / 50000 = 0.0002 BTC
        - base_amount = max(0.00001, 0.0002) = 0.0002 BTC (use min)
        """
        algo = make_oracle_algorithm(
            sell_percentage=0.01,
            min_sell_value=10.0,
        )
        portfolio = make_portfolio(current_asset_amount=0.001)  # Very small holding
        schedule = make_schedule(algorithm=algo, portfolio=portfolio)
        
        order = create_order(schedule, current_price=50000.0, previous_price=51500.0)
        assert order is not None
        assert order.direction == "sell"
        
        # Should use min_sell_value (0.0002 BTC) instead of percentage (0.00001 BTC)
        expected_base = 10.0 / 50000.0
        assert abs(order.base_amount - expected_base) < 0.0001


class TestArbitrageAlgorithmBuyOrder:
    """Arbitrage algorithm: buy order uses fixed_buy_value (not percentages)."""

    def test_arbitrage_buy_uses_fixed_value(self):
        """
        Arbitrage buy: base_amount = fixed_buy_value / current_price
        With fixed_buy_value=$100, price=$50,000:
        base_amount = 100 / 50000 = 0.002 BTC
        """
        algo = make_arbitrage_algorithm(fixed_buy_value=100.0)
        portfolio = make_portfolio()  # Portfolio is not used for amounts
        schedule = make_schedule(algorithm=algo, portfolio=portfolio)
        
        order = create_order(schedule, current_price=50000.0, previous_price=49500.0)
        assert order is not None
        assert order.direction == "buy"
        
        # Arbitrage uses fixed value, not percentage
        assert abs(order.quote_amount - 100.0) < 0.01
        expected_base = 100.0 / 50000.0
        assert abs(order.base_amount - expected_base) < 0.0001

    def test_arbitrage_ignores_oracle_fields(self):
        """
        Arbitrage algorithm should NOT use buy_percentage or min_buy_value.
        These fields should be 0 or ignored.
        """
        algo = make_arbitrage_algorithm(
            fixed_buy_value=100.0,
            buy_percentage=0.50,  # Should be ignored!
            min_buy_value=999.0,  # Should be ignored!
        )
        portfolio = make_portfolio(current_quote_amount=1000.0)  # Irrelevant
        schedule = make_schedule(algorithm=algo, portfolio=portfolio)
        
        order = create_order(schedule, current_price=50000.0, previous_price=49500.0)
        assert order is not None
        
        # Order should use fixed_buy_value, NOT (0.50 * 1000)
        assert abs(order.quote_amount - 100.0) < 0.01  # Fixed $100, not $500


class TestArbitrageAlgorithmSellOrder:
    """Arbitrage algorithm: sell order uses fixed_sell_value (not percentages)."""

    def test_arbitrage_sell_uses_fixed_value(self):
        """
        Arbitrage sell: base_amount = fixed_sell_value / current_price
        With fixed_sell_value=$100, price=$50,000:
        base_amount = 100 / 50000 = 0.002 BTC
        """
        algo = make_arbitrage_algorithm(fixed_sell_value=100.0)
        portfolio = make_portfolio()
        schedule = make_schedule(algorithm=algo, portfolio=portfolio)
        
        order = create_order(schedule, current_price=50000.0, previous_price=51500.0)
        assert order is not None
        assert order.direction == "sell"
        
        assert abs(order.quote_amount - 100.0) < 0.01
        expected_base = 100.0 / 50000.0
        assert abs(order.base_amount - expected_base) < 0.0001

    def test_arbitrage_ignores_oracle_fields_on_sell(self):
        """
        Arbitrage sell should NOT use sell_percentage or min_sell_value.
        """
        algo = make_arbitrage_algorithm(
            fixed_sell_value=100.0,
            sell_percentage=0.50,  # Should be ignored!
            min_sell_value=999.0,  # Should be ignored!
        )
        portfolio = make_portfolio(current_asset_amount=1.0)  # Irrelevant
        schedule = make_schedule(algorithm=algo, portfolio=portfolio)
        
        order = create_order(schedule, current_price=50000.0, previous_price=51500.0)
        assert order is not None
        
        # Order should use fixed_sell_value, NOT (0.50 * 1.0)
        assert abs(order.quote_amount - 100.0) < 0.01  # Fixed $100, not $25000


class TestAlgorithmFieldValidation:
    """
    Tests that validate oracle and arbitrage algorithms have correct fields set.
    Use these as smoke tests to catch configuration errors early.
    """

    def test_oracle_algorithm_fields_are_set(self):
        """Ensure oracle algorithm has all required percentage/value fields."""
        algo = make_oracle_algorithm()
        
        # Oracle must have these fields populated
        assert algo.buy_percentage > 0, "Oracle: buy_percentage must be > 0"
        assert algo.sell_percentage > 0, "Oracle: sell_percentage must be > 0"
        assert algo.min_buy_value > 0, "Oracle: min_buy_value must be > 0"
        assert algo.min_sell_value > 0, "Oracle: min_sell_value must be > 0"
        
        # Oracle should NOT use fixed values
        assert algo.fixed_buy_value == 0.0, "Oracle: fixed_buy_value should be 0"
        assert algo.fixed_sell_value == 0.0, "Oracle: fixed_sell_value should be 0"

    def test_arbitrage_algorithm_fields_are_set(self):
        """Ensure arbitrage algorithm has all required fixed-value fields."""
        algo = make_arbitrage_algorithm()
        
        # Arbitrage must have these fixed values
        assert algo.fixed_buy_value > 0, "Arbitrage: fixed_buy_value must be > 0"
        assert algo.fixed_sell_value > 0, "Arbitrage: fixed_sell_value must be > 0"
        
        # Arbitrage should NOT use percentages
        assert algo.buy_percentage == 0.0, "Arbitrage: buy_percentage should be 0"
        assert algo.sell_percentage == 0.0, "Arbitrage: sell_percentage should be 0"
        assert algo.min_buy_value == 0.0, "Arbitrage: min_buy_value should be 0"
        assert algo.min_sell_value == 0.0, "Arbitrage: min_sell_value should be 0"

    def test_different_algorithms_have_exclusive_fields(self):
        """Validate that oracle and arbitrage algorithms don't share active fields."""
        oracle = make_oracle_algorithm()
        arbitrage = make_arbitrage_algorithm()
        
        # Oracle active fields
        oracle_fields = (oracle.buy_percentage, oracle.sell_percentage, 
                        oracle.min_buy_value, oracle.min_sell_value)
        
        # Arbitrage active fields
        arbitrage_fields = (arbitrage.fixed_buy_value, arbitrage.fixed_sell_value)
        
        # No oracle fields should be in arbitrage active set
        for field in oracle_fields:
            assert field != arbitrage.fixed_buy_value
            assert field != arbitrage.fixed_sell_value
