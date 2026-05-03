import importlib
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from portfolio import Portfolio
from price import Price
from schedule import Schedule


def load_function_app_module():
    fake_functions = ModuleType("azure.functions")

    class FakeFunctionApp:
        def timer_trigger(self, *args, **kwargs):
            def decorator(fn):
                return fn

            return decorator

    fake_functions.FunctionApp = FakeFunctionApp
    fake_functions.TimerRequest = object

    fake_azure = ModuleType("azure")
    fake_azure.functions = fake_functions

    with patch.dict(sys.modules, {"azure": fake_azure, "azure.functions": fake_functions}):
        sys.modules.pop("function_app", None)
        return importlib.import_module("function_app")


def make_portfolio() -> Portfolio:
    return Portfolio(
        asset="BTC",
        quote="EUR",
        exchange="test",
        initial_asset_amount=0.0,
        initial_cost_basis=0.0,
        trades=[],
        current_cost_basis=0.0,
        current_asset_amount=0.0,
        current_quote_amount=0.0,
        cost_basis_value=0.0,
        market_value=0.0,
        last_updated=None,
    )


def make_schedule() -> Schedule:
    return Schedule(
        id="schedule-1",
        asset="BTC",
        quote="EUR",
        schedule="1H",
        last_execution=None,
        exchange="test",
        active=True,
        buy_and_sell=True,
        algorithm=None,
        portfolio=make_portfolio(),
    )


def make_price() -> Price:
    return Price(
        id="price-1",
        asset="BTC",
        quote="EUR",
        exchange="test",
        price=732.0,
        schedule=None,
        timestamp="2026-05-03T16:00:00.271123+00:00",
        active=True,
    )


def test_timer_function_persists_current_price_when_previous_price_missing():
    function_app = load_function_app_module()
    schedule = make_schedule()
    current_price = make_price()
    execution_timer = SimpleNamespace(past_due=False, schedule_status=None)

    with patch.object(function_app, "get_schedules", return_value=[schedule]), \
         patch.object(function_app, "check_exchange_connectivity", return_value=True), \
         patch.object(function_app, "update_trade", side_effect=AssertionError("update_trade should not be called")), \
         patch.object(function_app, "update_portfolio_trades", return_value=False), \
         patch.object(function_app, "update_schedule"), \
         patch.object(function_app, "get_current_price", return_value=current_price), \
         patch.object(function_app, "is_ready_for_next_execution", return_value=True), \
         patch.object(function_app, "get_previous_price", return_value=None), \
         patch.object(function_app, "create_order") as mock_create_order, \
         patch.object(function_app, "save_price") as mock_save_price, \
         patch.object(function_app, "register_execution") as mock_register_execution:
        function_app.timer_function(execution_timer)

    mock_create_order.assert_not_called()
    mock_save_price.assert_called_once_with(current_price)
    assert current_price.schedule == schedule.schedule
    mock_register_execution.assert_not_called()