"""
Unit tests for the Portfolio and Trade dataclasses (portfolio.py).
"""

import pytest
from portfolio import Trade, Portfolio


def make_trade(**overrides) -> Trade:
    defaults = dict(
        exchange_id="order-abc123",
        asset="BTC",
        quote="USD",
        amount=0.01,
        price=50000.0,
        direction="buy",
        exchange="coinbase",
        timestamp="2024-01-01T00:00:00",
        status="open",
        last_updated="2024-01-01T00:00:00",
    )
    defaults.update(overrides)
    return Trade(**defaults)


class TestTradeIsComplete:
    def test_filled_is_complete(self):
        assert make_trade(status="filled").is_complete() is True

    def test_cancelled_is_complete(self):
        assert make_trade(status="cancelled").is_complete() is True

    def test_rejected_is_complete(self):
        assert make_trade(status="rejected").is_complete() is True

    def test_open_is_not_complete(self):
        assert make_trade(status="open").is_complete() is False

    def test_pending_is_not_complete(self):
        assert make_trade(status="pending").is_complete() is False

    def test_dry_is_not_complete(self):
        assert make_trade(status="dry").is_complete() is False


class TestTradeIsFilled:
    def test_filled_is_filled(self):
        assert make_trade(status="filled").is_filled() is True

    def test_cancelled_is_not_filled(self):
        assert make_trade(status="cancelled").is_filled() is False

    def test_rejected_is_not_filled(self):
        assert make_trade(status="rejected").is_filled() is False

    def test_open_is_not_filled(self):
        assert make_trade(status="open").is_filled() is False


class TestTradeDataclass:
    def test_trade_fields_accessible(self):
        trade = make_trade()
        assert trade.asset == "BTC"
        assert trade.quote == "USD"
        assert trade.amount == 0.01
        assert trade.price == 50000.0
        assert trade.direction == "buy"
        assert trade.exchange == "coinbase"
