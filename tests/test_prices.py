"""
Unit tests for prices.py.

All Cosmos DB calls are mocked via repo.
"""

import pytest
from unittest.mock import patch, MagicMock

from price import Price
import prices as prices_module


def make_price(**overrides) -> Price:
    defaults = dict(
        asset="BTC",
        quote="USD",
        exchange="test",
        price=50000.0,
        schedule="1H",
        timestamp="2024-01-01T00:00:00",
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
