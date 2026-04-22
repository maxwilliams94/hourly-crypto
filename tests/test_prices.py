"""
Unit tests for prices.py.

All Cosmos DB calls are mocked via repo.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from price import Price
import prices as prices_module


def make_price(**overrides) -> Price:
    recent_ts = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    defaults = dict(
        id="price-1",
        asset="BTC",
        quote="USD",
        exchange="test",
        price=50000.0,
        schedule="1H",
        timestamp=recent_ts,
        active=True,
    )
    defaults.update(overrides)
    return Price(**defaults)


# ---------------------------------------------------------------------------
# save_price
# ---------------------------------------------------------------------------

class TestSavePrice:
    def test_delegates_to_persist_price(self):
        price = make_price()
        with patch("prices.persist_price") as mock_persist:
            prices_module.save_price(price)
            mock_persist.assert_called_once_with(price)


# ---------------------------------------------------------------------------
# get_previous_price
# ---------------------------------------------------------------------------

class TestGetPreviousPrice:
    def test_returns_first_result_when_prices_exist(self):
        expected = make_price(price=48000.0)
        with patch("prices.get_prices", return_value=[expected]) as mock_get:
            result = prices_module.get_previous_price("BTC", "USD", "1H", "test")
            mock_get.assert_called_once_with("BTC", "USD", "1H", "test", 1)
            assert result == expected

    def test_returns_none_when_no_prices(self):
        with patch("prices.get_prices", return_value=[]):
            result = prices_module.get_previous_price("BTC", "USD", "1H", "test")
            assert result is None

    def test_passes_correct_arguments_to_repo(self):
        with patch("prices.get_prices", return_value=[]) as mock_get:
            prices_module.get_previous_price("ETH", "GBP", "4H", "coinbase")
            mock_get.assert_called_once_with("ETH", "GBP", "4H", "coinbase", 1)

    def test_returns_none_and_warns_when_price_is_stale(self):
        stale_ts = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        stale_price = make_price(timestamp=stale_ts)
        with patch("prices.get_prices", return_value=[stale_price]):
            with patch("prices.logging") as mock_log:
                result = prices_module.get_previous_price("BTC", "USD", "1H", "test")
                assert result is None
                mock_log.warning.assert_called_once()

    def test_returns_price_just_within_tolerance(self):
        # 1H * 1.1 = 66 minutes; 65 minutes ago is within tolerance
        fresh_ts = (datetime.now(timezone.utc) - timedelta(minutes=65)).isoformat()
        fresh_price = make_price(timestamp=fresh_ts)
        with patch("prices.get_prices", return_value=[fresh_price]):
            result = prices_module.get_previous_price("BTC", "USD", "1H", "test")
            assert result == fresh_price

    def test_returns_none_just_outside_tolerance(self):
        # 1H * 1.1 = 66 minutes; 67 minutes ago exceeds tolerance
        stale_ts = (datetime.now(timezone.utc) - timedelta(minutes=67)).isoformat()
        stale_price = make_price(timestamp=stale_ts)
        with patch("prices.get_prices", return_value=[stale_price]):
            result = prices_module.get_previous_price("BTC", "USD", "1H", "test")
            assert result is None

    def test_skips_staleness_check_for_unknown_schedule(self):
        old_ts = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        price = make_price(timestamp=old_ts, schedule="CUSTOM")
        with patch("prices.get_prices", return_value=[price]):
            result = prices_module.get_previous_price("BTC", "USD", "CUSTOM", "test")
            assert result == price

    def test_returns_none_and_warns_when_timestamp_is_none(self):
        price = make_price(timestamp=None)
        with patch("prices.get_prices", return_value=[price]):
            with patch("prices.logging") as mock_log:
                result = prices_module.get_previous_price("BTC", "USD", "1H", "test")
                assert result is None
                mock_log.warning.assert_called_once()
