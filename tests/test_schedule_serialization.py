"""
Unit tests for Schedule JSON serialization (schedule.py).

Tests that Schedule, Algorithm, Portfolio, and Trade objects can be
properly serialized to JSON and deserialized back.
"""

import json
import pytest
from algorithm import Algorithm
from portfolio import Trade, Portfolio
from schedule import Schedule


def make_algorithm(**overrides) -> Algorithm:
    """Factory for creating Algorithm instances with default values."""
    defaults = dict(
        name="test-algo",
        description="Test algorithm",
        algo_type="oracle",
        buy_threshold=30000.0,
        sell_threshold=50000.0,
        sell_below_cost_basis=False,
        buy_percentage=10.0,
        sell_percentage=20.0,
        min_buy_value=100.0,
        min_sell_value=100.0,
        fixed_buy_value=0.0,
        fixed_sell_value=0.0,
        minimum_profit_percentage=2.0,
    )
    defaults.update(overrides)
    return Algorithm(**defaults)


def make_trade(**overrides) -> Trade:
    """Factory for creating Trade instances with default values."""
    defaults = dict(
        id="trade-1",
        exchange_id="order-abc123",
        asset="BTC",
        quote="USD",
        amount=0.01,
        price=50000.0,
        direction="buy",
        exchange="coinbase",
        timestamp="2024-01-01T00:00:00",
        status="filled",
        last_updated="2024-01-01T00:00:00",
    )
    defaults.update(overrides)
    return Trade(**defaults)


def make_portfolio(**overrides) -> Portfolio:
    """Factory for creating Portfolio instances with default values."""
    defaults = dict(
        asset="BTC",
        quote="USD",
        exchange="coinbase",
        initial_asset_amount=1.0,
        initial_cost_basis=50000.0,
        trades=[make_trade()],
        current_cost_basis=50000.0,
        current_asset_amount=1.0,
        current_quote_amount=0.0,
        cost_basis_value=40000.0,  # 1.0 * 40000
        market_value=50000.0,      # 1.0 * 50000 (assuming current price is higher)
        last_updated="2024-01-01T00:00:00",
        initial_quote_amount=50000.0,
    )
    defaults.update(overrides)
    return Portfolio(**defaults)


def make_schedule(**overrides) -> Schedule:
    """Factory for creating Schedule instances with default values."""
    defaults = dict(
        id="schedule-1",
        asset="BTC",
        quote="USD",
        schedule="hourly",
        last_execution="2024-01-01T00:00:00",
        exchange="coinbase",
        active=True,
        buy_and_sell=True,
        algorithm=make_algorithm(),
        portfolio=make_portfolio(),
    )
    defaults.update(overrides)
    return Schedule(**defaults)


class TestAlgorithmSerialization:
    """Test Algorithm to_dict() and from_dict() methods."""

    def test_algorithm_to_dict(self):
        """Test that Algorithm.to_dict() returns a proper dictionary."""
        algo = make_algorithm()
        data = algo.to_dict()
        
        assert isinstance(data, dict)
        assert data['name'] == "test-algo"
        assert data['algo_type'] == "oracle"
        assert data['buy_threshold'] == 30000.0

    def test_algorithm_to_dict_is_json_serializable(self):
        """Test that Algorithm can be serialized to JSON."""
        algo = make_algorithm()
        data = algo.to_dict()
        
        # Should not raise TypeError
        json_str = json.dumps(data)
        assert json_str is not None

    def test_algorithm_from_dict_then_to_dict_roundtrip(self):
        """Test roundtrip: object -> dict -> json -> dict -> object."""
        algo1 = make_algorithm(name="special-algo", buy_threshold=25000.0)
        data1 = algo1.to_dict()
        json_str = json.dumps(data1)
        data2 = json.loads(json_str)
        algo2 = Algorithm.from_dict(data2)
        
        assert algo1.name == algo2.name
        assert algo1.algo_type == algo2.algo_type
        assert algo1.buy_threshold == algo2.buy_threshold


class TestTradeSerialization:
    """Test Trade to_dict() and from_dict() methods."""

    def test_trade_to_dict(self):
        """Test that Trade.to_dict() returns a proper dictionary."""
        trade = make_trade()
        data = trade.to_dict()
        
        assert isinstance(data, dict)
        assert data['id'] == "trade-1"
        assert data['amount'] == 0.01
        assert data['direction'] == "buy"

    def test_trade_to_dict_is_json_serializable(self):
        """Test that Trade can be serialized to JSON."""
        trade = make_trade()
        data = trade.to_dict()
        
        # Should not raise TypeError
        json_str = json.dumps(data)
        assert json_str is not None

    def test_trade_from_dict_then_to_dict_roundtrip(self):
        """Test roundtrip: object -> dict -> json -> dict -> object."""
        trade1 = make_trade(id="special-trade", amount=0.5)
        data1 = trade1.to_dict()
        json_str = json.dumps(data1)
        data2 = json.loads(json_str)
        trade2 = Trade.from_dict(data2)
        
        assert trade1.id == trade2.id
        assert trade1.amount == trade2.amount
        assert trade1.direction == trade2.direction


class TestPortfolioSerialization:
    """Test Portfolio to_dict() and from_dict() methods."""

    def test_portfolio_to_dict(self):
        """Test that Portfolio.to_dict() returns a proper dictionary."""
        portfolio = make_portfolio()
        data = portfolio.to_dict()
        
        assert isinstance(data, dict)
        assert data['asset'] == "BTC"
        assert data['current_asset_amount'] == 1.0
        assert isinstance(data['trades'], list)
        assert len(data['trades']) == 1

    def test_portfolio_to_dict_is_json_serializable(self):
        """Test that Portfolio can be serialized to JSON."""
        portfolio = make_portfolio()
        data = portfolio.to_dict()
        
        # Should not raise TypeError
        json_str = json.dumps(data)
        assert json_str is not None

    def test_portfolio_to_dict_with_multiple_trades(self):
        """Test Portfolio serialization with multiple trades."""
        trades = [make_trade(id=f"trade-{i}") for i in range(3)]
        portfolio = make_portfolio(trades=trades)
        data = portfolio.to_dict()
        
        assert len(data['trades']) == 3
        assert all(isinstance(t, dict) for t in data['trades'])
        
        # Should be JSON serializable
        json_str = json.dumps(data)
        assert json_str is not None

    def test_portfolio_from_dict_then_to_dict_roundtrip(self):
        """Test roundtrip: object -> dict -> json -> dict -> object."""
        portfolio1 = make_portfolio(
            asset="ETH",
            current_asset_amount=10.0,
            trades=[make_trade(id="eth-trade")]
        )
        data1 = portfolio1.to_dict()
        json_str = json.dumps(data1)
        data2 = json.loads(json_str)
        portfolio2 = Portfolio.from_dict(data2)
        
        assert portfolio1.asset == portfolio2.asset
        assert portfolio1.current_asset_amount == portfolio2.current_asset_amount
        assert len(portfolio1.trades) == len(portfolio2.trades)


class TestScheduleSerialization:
    """Test Schedule to_dict() and from_dict() methods."""

    def test_schedule_to_dict(self):
        """Test that Schedule.to_dict() returns a proper dictionary."""
        schedule = make_schedule()
        data = schedule.to_dict()
        
        assert isinstance(data, dict)
        assert data['id'] == "schedule-1"
        assert data['asset'] == "BTC"
        assert data['active'] is True
        assert isinstance(data['algorithm'], dict)
        assert isinstance(data['portfolio'], dict)

    def test_schedule_to_dict_is_json_serializable(self):
        """Test that Schedule can be serialized to JSON without TypeError."""
        schedule = make_schedule()
        data = schedule.to_dict()
        
        # This is the key test: should not raise TypeError about Algorithm
        json_str = json.dumps(data)
        assert json_str is not None

    def test_schedule_nested_algorithm_serialized(self):
        """Test that nested Algorithm is properly serialized to dict."""
        algo = make_algorithm(name="nested-algo")
        schedule = make_schedule(algorithm=algo)
        data = schedule.to_dict()
        
        assert isinstance(data['algorithm'], dict)
        assert data['algorithm']['name'] == "nested-algo"
        assert data['algorithm']['buy_threshold'] == 30000.0

    def test_schedule_nested_portfolio_serialized(self):
        """Test that nested Portfolio is properly serialized to dict."""
        portfolio = make_portfolio(asset="ETH")
        schedule = make_schedule(portfolio=portfolio)
        data = schedule.to_dict()
        
        assert isinstance(data['portfolio'], dict)
        assert data['portfolio']['asset'] == "ETH"
        assert isinstance(data['portfolio']['trades'], list)

    def test_schedule_from_dict_then_to_dict_roundtrip(self):
        """Test roundtrip: object -> dict -> json -> dict -> object."""
        schedule1 = make_schedule(
            id="special-schedule",
            asset="ETH",
            active=False,
            algorithm=make_algorithm(name="eth-algo"),
            portfolio=make_portfolio(asset="ETH"),
        )
        data1 = schedule1.to_dict()
        json_str = json.dumps(data1)
        data2 = json.loads(json_str)
        schedule2 = Schedule.from_dict(data2)
        
        assert schedule1.id == schedule2.id
        assert schedule1.asset == schedule2.asset
        assert schedule1.active == schedule2.active
        assert schedule1.algorithm.name == schedule2.algorithm.name
        assert schedule1.portfolio.asset == schedule2.portfolio.asset

    def test_schedule_full_json_roundtrip(self):
        """Test full roundtrip: object -> JSON string -> object."""
        schedule1 = make_schedule(
            id="full-test",
            algorithm=make_algorithm(buy_percentage=15.0),
            portfolio=make_portfolio(trades=[make_trade(), make_trade(id="trade-2")]),
        )
        
        # Serialize to JSON
        json_str = json.dumps(schedule1.to_dict())
        
        # Deserialize back
        data = json.loads(json_str)
        schedule2 = Schedule.from_dict(data)
        
        # Re-serialize to JSON
        json_str2 = json.dumps(schedule2.to_dict())
        
        # Should be idempotent
        assert json_str == json_str2
        assert schedule1.id == schedule2.id
        assert schedule1.algorithm.buy_percentage == schedule2.algorithm.buy_percentage
        assert len(schedule1.portfolio.trades) == len(schedule2.portfolio.trades)
