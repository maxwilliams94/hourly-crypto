"""
Unit tests for the Portfolio and Trade dataclasses (portfolio.py).
"""

import pytest
from portfolio import Trade, Portfolio, update_portfolio_trades, EXCHANGE_FEE_RATES


def make_trade(**overrides) -> Trade:
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


# ---------------------------------------------------------------------------
# Helpers for Portfolio tests
# ---------------------------------------------------------------------------

def make_portfolio(**overrides) -> Portfolio:
    defaults = dict(
        asset="BTC",
        quote="USD",
        exchange="coinbase",
        initial_asset_amount=0.0,
        initial_cost_basis=0.0,
        initial_quote_amount=0.0,
        trades=[],
        current_cost_basis=0.0,
        current_asset_amount=0.0,
        current_quote_amount=0.0,
        cost_basis_value=0.0,
        market_value=0.0,
        last_updated=None,
    )
    defaults.update(overrides)
    return Portfolio(**defaults)


def make_filled_trade(**overrides) -> Trade:
    """A trade that is already filled, with a timestamp newer than any portfolio last_updated."""
    defaults = dict(
        id="trade-filled",
        exchange_id="order-filled",
        asset="BTC",
        quote="USD",
        amount=0.5,
        price=40000.0,
        direction="buy",
        exchange="coinbase",
        timestamp="2024-06-01T12:00:00",
        status="filled",
        last_updated="2024-06-01T12:00:00",
        fee=None,
    )
    defaults.update(overrides)
    return Trade(**defaults)


# ---------------------------------------------------------------------------
# update_portfolio_trades tests
# ---------------------------------------------------------------------------

class TestUpdatePortfolioTrades:

    # -- Skip conditions -----------------------------------------------------

    def test_returns_false_for_none_portfolio(self):
        assert update_portfolio_trades(None) is False

    def test_no_trades_no_update(self):
        portfolio = make_portfolio()
        assert update_portfolio_trades(portfolio) is False

    def test_no_filled_trades_skips_update(self):
        open_trade = make_filled_trade(status="open", last_updated="2024-06-01T12:00:00")
        portfolio = make_portfolio(trades=[open_trade])
        assert update_portfolio_trades(portfolio) is False

    def test_no_new_filled_trades_since_last_update_skips(self):
        # Trade last_updated is before portfolio.last_updated
        trade = make_filled_trade(last_updated="2024-01-01T00:00:00")
        portfolio = make_portfolio(trades=[trade], last_updated="2024-06-01T00:00:00")
        assert update_portfolio_trades(portfolio) is False

    def test_cancelled_trade_not_counted(self):
        trade = make_filled_trade(status="cancelled", last_updated="2024-06-01T12:00:00")
        portfolio = make_portfolio(trades=[trade])
        assert update_portfolio_trades(portfolio) is False

    # -- Basic buy -----------------------------------------------------------

    def test_single_buy_from_zero_holdings(self):
        # 0.5 BTC at 40 000 → cost basis = 40 000, asset = 0.5, quote reduced (fee=0 to isolate)
        trade = make_filled_trade(amount=0.5, price=40000.0, direction="buy", fee=0.0)
        portfolio = make_portfolio(initial_quote_amount=20000.0, trades=[trade])

        result = update_portfolio_trades(portfolio)

        assert result is True
        assert portfolio.current_asset_amount == pytest.approx(0.5)
        assert portfolio.current_cost_basis == pytest.approx(40000.0)
        assert portfolio.current_quote_amount == pytest.approx(0.0)   # 20 000 − 0.5×40 000

    def test_buy_adds_to_initial_holdings(self):
        # 0.5 BTC @ 30 000 initially, buy 0.5 more @ 50 000 (fee=0 to isolate)
        # Average = (0.5×30 000 + 0.5×50 000) / 1.0 = 40 000
        trade = make_filled_trade(amount=0.5, price=50000.0, direction="buy", fee=0.0)
        portfolio = make_portfolio(
            initial_asset_amount=0.5,
            initial_cost_basis=30000.0,
            initial_quote_amount=25000.0,
            trades=[trade],
        )

        result = update_portfolio_trades(portfolio)

        assert result is True
        assert portfolio.current_asset_amount == pytest.approx(1.0)
        assert portfolio.current_cost_basis == pytest.approx(40000.0)
        assert portfolio.current_quote_amount == pytest.approx(0.0)   # 25 000 − 0.5×50 000

    def test_multiple_buys_weighted_average(self):
        # 0.5 BTC @ 20 000 + 1.0 BTC @ 40 000 → avg = (10 000 + 40 000) / 1.5 ≈ 33 333.33 (fee=0)
        t1 = make_filled_trade(id="t1", amount=0.5, price=20000.0, direction="buy",
                               timestamp="2024-01-01T10:00:00", last_updated="2024-01-01T10:00:00",
                               fee=0.0)
        t2 = make_filled_trade(id="t2", amount=1.0, price=40000.0, direction="buy",
                               timestamp="2024-01-01T11:00:00", last_updated="2024-01-01T11:00:00",
                               fee=0.0)
        portfolio = make_portfolio(initial_quote_amount=50000.0, trades=[t1, t2])

        update_portfolio_trades(portfolio)

        assert portfolio.current_asset_amount == pytest.approx(1.5)
        assert portfolio.current_cost_basis == pytest.approx((10000.0 + 40000.0) / 1.5)
        assert portfolio.current_quote_amount == pytest.approx(50000.0 - 10000.0 - 40000.0)

    # -- Sell ----------------------------------------------------------------

    def test_sell_reduces_amount_not_cost_basis(self):
        # 1 BTC @ 40 000 initially; sell 0.5 @ 50 000 (fee=0 to isolate)
        # Average cost method: cost basis per unit stays 40 000 after a sell
        trade = make_filled_trade(amount=0.5, price=50000.0, direction="sell", fee=0.0)
        portfolio = make_portfolio(
            initial_asset_amount=1.0,
            initial_cost_basis=40000.0,
            initial_quote_amount=0.0,
            trades=[trade],
        )

        update_portfolio_trades(portfolio)

        assert portfolio.current_asset_amount == pytest.approx(0.5)
        assert portfolio.current_cost_basis == pytest.approx(40000.0)  # unchanged
        assert portfolio.current_quote_amount == pytest.approx(25000.0)  # 0 + 0.5×50 000

    # -- Mixed buy + sell ----------------------------------------------------

    def test_buy_then_sell_sequence(self):
        # Start empty (no initial holdings). fee=0 to isolate buy/sell logic.
        # Buy 1 BTC @ 30 000 → basis 30 000, amount 1
        # Buy 1 BTC @ 50 000 → avg basis 40 000, amount 2
        # Sell 1 BTC @ 45 000 → basis stays 40 000, amount 1
        t_buy1 = make_filled_trade(id="b1", amount=1.0, price=30000.0, direction="buy",
                                   timestamp="2024-01-01T10:00:00", last_updated="2024-01-01T10:00:00",
                                   fee=0.0)
        t_buy2 = make_filled_trade(id="b2", amount=1.0, price=50000.0, direction="buy",
                                   timestamp="2024-01-01T11:00:00", last_updated="2024-01-01T11:00:00",
                                   fee=0.0)
        t_sell = make_filled_trade(id="s1", amount=1.0, price=45000.0, direction="sell",
                                   timestamp="2024-01-01T12:00:00", last_updated="2024-01-01T12:00:00",
                                   fee=0.0)
        portfolio = make_portfolio(
            initial_quote_amount=80000.0,
            trades=[t_buy1, t_buy2, t_sell],
        )

        update_portfolio_trades(portfolio)

        assert portfolio.current_asset_amount == pytest.approx(1.0)
        assert portfolio.current_cost_basis == pytest.approx(40000.0)
        # quote: 80 000 − 30 000 − 50 000 + 45 000 = 45 000
        assert portfolio.current_quote_amount == pytest.approx(45000.0)

    # -- last_updated --------------------------------------------------------

    def test_last_updated_set_on_successful_update(self):
        trade = make_filled_trade()
        portfolio = make_portfolio(trades=[trade])
        update_portfolio_trades(portfolio)
        assert portfolio.last_updated is not None

    def test_update_runs_when_portfolio_never_updated_and_has_filled_trade(self):
        # last_updated is None and there is a filled trade → should update
        trade = make_filled_trade()
        portfolio = make_portfolio(trades=[trade], last_updated=None)
        assert update_portfolio_trades(portfolio) is True

    def test_update_runs_when_trade_is_newer_than_last_updated(self):
        trade = make_filled_trade(last_updated="2024-06-02T00:00:00")
        portfolio = make_portfolio(trades=[trade], last_updated="2024-06-01T00:00:00")
        assert update_portfolio_trades(portfolio) is True

    def test_update_handles_mixed_naive_and_aware_last_updated(self):
        trade = make_filled_trade(last_updated="2024-06-01T12:30:00")
        portfolio = make_portfolio(
            trades=[trade],
            last_updated="2024-06-01T12:00:00+00:00",
        )

        assert update_portfolio_trades(portfolio) is True

    # -- initial_quote_amount field ------------------------------------------

    def test_initial_quote_amount_defaults_to_zero(self):
        portfolio = make_portfolio()
        portfolio_no_quote = Portfolio(
            asset="BTC", quote="USD", exchange="coinbase",
            initial_asset_amount=0.0, initial_cost_basis=0.0,
            trades=[], current_cost_basis=0.0, current_asset_amount=0.0,
            current_quote_amount=0.0, cost_basis_value=0.0, market_value=0.0, last_updated=None,
        )
        assert portfolio.initial_quote_amount == pytest.approx(0.0)
        assert portfolio_no_quote.initial_quote_amount == pytest.approx(0.0)

    def test_from_dict_accepts_initial_quote_amount(self):
        data = {
            "asset": "BTC", "quote": "USD", "exchange": "coinbase",
            "initial_asset_amount": 1.0, "initial_cost_basis": 30000.0,
            "initial_quote_amount": 5000.0,
            "trades": [], "current_cost_basis": 30000.0,
            "current_asset_amount": 1.0, "current_quote_amount": 5000.0,
            "cost_basis_value": 30000.0, "market_value": 30000.0, "last_updated": None,
        }
        portfolio = Portfolio.from_dict(data)
        assert portfolio.initial_quote_amount == pytest.approx(5000.0)

    def test_from_dict_without_initial_quote_amount_uses_default(self):
        data = {
            "asset": "BTC", "quote": "USD", "exchange": "coinbase",
            "initial_asset_amount": 1.0, "initial_cost_basis": 30000.0,
            "trades": [], "current_cost_basis": 30000.0,
            "current_asset_amount": 1.0, "current_quote_amount": 0.0,
            "cost_basis_value": 30000.0, "market_value": 30000.0, "last_updated": None,
        }
        portfolio = Portfolio.from_dict(data)
        assert portfolio.initial_quote_amount == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Fee tests
# ---------------------------------------------------------------------------

class TestFees:

    def test_coinbase_fee_rate_is_075_percent(self):
        assert EXCHANGE_FEE_RATES["coinbase"] == pytest.approx(0.0075)

    def test_buy_deducts_fee_from_quote(self):
        # 0.5 BTC @ 40 000 on coinbase
        # trade_cost = 20 000, fee = 20 000 * 0.0075 = 150
        # quote: 25 000 - 20 000 - 150 = 4 850
        trade = make_filled_trade(amount=0.5, price=40000.0, direction="buy", fee=None)
        portfolio = make_portfolio(initial_quote_amount=25000.0, trades=[trade])

        update_portfolio_trades(portfolio)

        trade_cost = 0.5 * 40000.0
        fee = trade_cost * EXCHANGE_FEE_RATES["coinbase"]
        assert portfolio.current_quote_amount == pytest.approx(25000.0 - trade_cost - fee)

    def test_sell_deducts_fee_from_quote(self):
        # 1 BTC @ 40 000 initially; sell 0.5 @ 50 000 on coinbase
        # trade_cost = 25 000, fee = 25 000 * 0.0075 = 187.50
        # quote: 0 + 25 000 - 187.50 = 24 812.50
        trade = make_filled_trade(amount=0.5, price=50000.0, direction="sell", fee=None)
        portfolio = make_portfolio(
            initial_asset_amount=1.0,
            initial_cost_basis=40000.0,
            initial_quote_amount=0.0,
            trades=[trade],
        )

        update_portfolio_trades(portfolio)

        trade_cost = 0.5 * 50000.0
        fee = trade_cost * EXCHANGE_FEE_RATES["coinbase"]
        assert portfolio.current_quote_amount == pytest.approx(trade_cost - fee)

    def test_explicit_fee_overrides_default_rate(self):
        # Providing a specific fee amount bypasses the exchange default
        explicit_fee = 50.0
        trade = make_filled_trade(amount=0.5, price=40000.0, direction="buy", fee=explicit_fee)
        portfolio = make_portfolio(initial_quote_amount=25000.0, trades=[trade])

        update_portfolio_trades(portfolio)

        trade_cost = 0.5 * 40000.0
        assert portfolio.current_quote_amount == pytest.approx(25000.0 - trade_cost - explicit_fee)

    def test_zero_explicit_fee_not_overridden_by_default(self):
        # fee=0.0 means no fee was charged (e.g. promo), not "use default"
        trade = make_filled_trade(amount=0.5, price=40000.0, direction="buy", fee=0.0)
        portfolio = make_portfolio(initial_quote_amount=20000.0, trades=[trade])

        update_portfolio_trades(portfolio)

        trade_cost = 0.5 * 40000.0
        assert portfolio.current_quote_amount == pytest.approx(20000.0 - trade_cost)  # no fee

    def test_unknown_exchange_falls_back_to_zero_fee(self):
        # Exchange not in EXCHANGE_FEE_RATES → fee defaults to 0
        trade = make_filled_trade(
            amount=1.0, price=30000.0, direction="buy",
            exchange="unknown_exchange", fee=None,
        )
        portfolio = make_portfolio(initial_quote_amount=30000.0, trades=[trade])

        update_portfolio_trades(portfolio)

        assert portfolio.current_quote_amount == pytest.approx(0.0)  # 30 000 - 30 000 - 0

    def test_fee_does_not_affect_cost_basis(self):
        # Fee is fiat-only; it must not alter cost basis or asset amount
        trade = make_filled_trade(amount=0.5, price=40000.0, direction="buy", fee=None)
        portfolio = make_portfolio(initial_quote_amount=25000.0, trades=[trade])

        update_portfolio_trades(portfolio)

        assert portfolio.current_asset_amount == pytest.approx(0.5)
        assert portfolio.current_cost_basis == pytest.approx(40000.0)

    def test_from_dict_trade_fee_round_trips(self):
        data = {
            "id": "t1", "exchange_id": "e1", "asset": "BTC", "quote": "USD",
            "amount": 0.5, "price": 40000.0, "direction": "buy", "exchange": "coinbase",
            "timestamp": "2024-01-01T00:00:00", "status": "filled",
            "last_updated": "2024-01-01T00:00:00", "fee": 150.0,
        }
        trade = Trade.from_dict(data)
        assert trade.fee == pytest.approx(150.0)

    def test_from_dict_trade_fee_defaults_to_none(self):
        data = {
            "id": "t1", "exchange_id": "e1", "asset": "BTC", "quote": "USD",
            "amount": 0.5, "price": 40000.0, "direction": "buy", "exchange": "coinbase",
            "timestamp": "2024-01-01T00:00:00", "status": "filled",
            "last_updated": "2024-01-01T00:00:00",
        }
        trade = Trade.from_dict(data)
        assert trade.fee is None
