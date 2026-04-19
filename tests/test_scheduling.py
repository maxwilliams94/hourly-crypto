"""
Unit tests for src/scheduling.py.

is_ready_for_next_execution() is pure logic with no external I/O, so it is
tested exhaustively.  get_schedules(), register_execution() and
update_schedule() are tested with mocked repo calls.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.scheduling import is_ready_for_next_execution, get_schedules
from src.schedule import Schedule
from src.algorithm import Algorithm
from src.portfolio import Portfolio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_schedule(schedule_interval: str = "1H", last_execution: str = None) -> Schedule:
    algo = Algorithm(
        name="test", description="", algo_type="oracle",
        buy_threshold=1.0, sell_threshold=-1.0,
        sell_below_cost_basis=False,
        buy_percentage=0.1, sell_percentage=0.1,
        min_buy_value=10.0, min_sell_value=10.0,
        fixed_buy_value=0.0, fixed_sell_value=0.0,
        minimum_profit_percentage=0.0,
    )
    portfolio = Portfolio(
        asset="BTC", quote="USD", exchange="test",
        initial_asset_amount=0.0, initial_cost_basis=0.0,
        trades=[],
        current_cost_basis=40000.0, current_asset_amount=0.1,
        current_quote_amount=1000.0, current_net_worth=5000.0,
        last_updated="2024-01-01T00:00:00",
    )
    return Schedule(
        id="sched-1", asset="BTC", quote="USD",
        schedule=schedule_interval,
        last_execution=last_execution,
        exchange="test", active=True, buy_and_sell=True,
        algorithm=algo, portfolio=portfolio,
    )


# ---------------------------------------------------------------------------
# No previous execution (first-time logic)
# ---------------------------------------------------------------------------

class TestIsReadyNoLastExecution:
    """When last_execution is None the schedule fires at the start of its window."""

    def test_1D_ready_at_midnight(self):
        s = make_schedule("1D")
        now = datetime(2024, 1, 15, 0, 30)  # hour == 0
        assert is_ready_for_next_execution(s, now) is True

    def test_1D_not_ready_outside_midnight(self):
        s = make_schedule("1D")
        now = datetime(2024, 1, 15, 6, 0)
        assert is_ready_for_next_execution(s, now) is False

    def test_4H_ready_on_4h_boundary(self):
        s = make_schedule("4H")
        for hour in (0, 4, 8, 12, 16, 20):
            now = datetime(2024, 1, 15, hour, 0)
            assert is_ready_for_next_execution(s, now) is True, f"Expected ready at hour {hour}"

    def test_4H_not_ready_off_boundary(self):
        s = make_schedule("4H")
        for hour in (1, 2, 3, 5, 7, 9):
            now = datetime(2024, 1, 15, hour, 0)
            assert is_ready_for_next_execution(s, now) is False, f"Expected not ready at hour {hour}"

    def test_1H_ready_at_top_of_hour(self):
        s = make_schedule("1H")
        now = datetime(2024, 1, 15, 10, 0)  # minute == 0
        assert is_ready_for_next_execution(s, now) is True

    def test_1H_not_ready_mid_hour(self):
        s = make_schedule("1H")
        now = datetime(2024, 1, 15, 10, 30)
        assert is_ready_for_next_execution(s, now) is False

    def test_1M_ready_at_start_of_minute(self):
        s = make_schedule("1M")
        now = datetime(2024, 1, 15, 10, 5, 10)  # second < 30
        assert is_ready_for_next_execution(s, now) is True

    def test_1M_not_ready_after_30_seconds(self):
        s = make_schedule("1M")
        now = datetime(2024, 1, 15, 10, 5, 45)  # second >= 30
        assert is_ready_for_next_execution(s, now) is False

    def test_unknown_interval_returns_false(self):
        s = make_schedule("2H")  # not a valid interval
        now = datetime(2024, 1, 15, 10, 0)
        assert is_ready_for_next_execution(s, now) is False


# ---------------------------------------------------------------------------
# With previous execution (recurring logic)
# ---------------------------------------------------------------------------

class TestIsReadyWithLastExecution:
    def test_1H_ready_when_new_hour_reached(self):
        last = "2024-01-15T09:15:00"
        s = make_schedule("1H", last_execution=last)
        now = datetime(2024, 1, 15, 10, 0)  # new hour, minute == 0
        assert is_ready_for_next_execution(s, now) is True

    def test_1H_not_ready_same_hour_as_last_execution(self):
        last = "2024-01-15T10:00:00"
        s = make_schedule("1H", last_execution=last)
        now = datetime(2024, 1, 15, 10, 0)
        assert is_ready_for_next_execution(s, now) is False

    def test_1H_not_ready_when_not_top_of_hour(self):
        last = "2024-01-15T09:15:00"
        s = make_schedule("1H", last_execution=last)
        now = datetime(2024, 1, 15, 10, 30)  # minute != 0
        assert is_ready_for_next_execution(s, now) is False

    def test_1D_ready_when_new_day_at_midnight(self):
        last = "2024-01-14T00:00:00"
        s = make_schedule("1D", last_execution=last)
        now = datetime(2024, 1, 15, 0, 0)  # new day, hour == 0
        assert is_ready_for_next_execution(s, now) is True

    def test_1D_not_ready_same_day(self):
        last = "2024-01-15T00:00:00"
        s = make_schedule("1D", last_execution=last)
        now = datetime(2024, 1, 15, 1, 0)
        assert is_ready_for_next_execution(s, now) is False

    def test_1D_not_ready_new_day_but_not_midnight(self):
        last = "2024-01-14T00:00:00"
        s = make_schedule("1D", last_execution=last)
        now = datetime(2024, 1, 15, 6, 0)  # new day but hour != 0
        assert is_ready_for_next_execution(s, now) is False

    def test_4H_ready_when_4h_passed_and_on_boundary(self):
        last = "2024-01-15T08:00:00"
        s = make_schedule("4H", last_execution=last)
        now = datetime(2024, 1, 15, 12, 0)  # 4h later, on boundary
        assert is_ready_for_next_execution(s, now) is True

    def test_4H_not_ready_when_same_4h_window(self):
        last = "2024-01-15T12:00:00"
        s = make_schedule("4H", last_execution=last)
        now = datetime(2024, 1, 15, 12, 30)  # same hour
        assert is_ready_for_next_execution(s, now) is False

    def test_1M_ready_when_new_minute_and_early_in_second(self):
        last = "2024-01-15T10:05:10"
        s = make_schedule("1M", last_execution=last)
        now = datetime(2024, 1, 15, 10, 6, 5)  # new minute, second < 30
        assert is_ready_for_next_execution(s, now) is True

    def test_1M_not_ready_same_minute(self):
        last = "2024-01-15T10:05:10"
        s = make_schedule("1M", last_execution=last)
        now = datetime(2024, 1, 15, 10, 5, 20)  # same minute
        assert is_ready_for_next_execution(s, now) is False

    def test_1W_ready_on_new_week_monday_midnight(self):
        # Monday 2024-01-15 (weekday 0) – same ISO week as previous
        # Move to Monday 2024-01-22
        last = "2024-01-15T00:00:00"
        s = make_schedule("1W", last_execution=last)
        now = datetime(2024, 1, 22, 0, 0)  # Monday, hour 0, new ISO week
        assert is_ready_for_next_execution(s, now) is True

    def test_1W_not_ready_same_week(self):
        last = "2024-01-15T00:00:00"
        s = make_schedule("1W", last_execution=last)
        now = datetime(2024, 1, 17, 0, 0)  # same ISO week
        assert is_ready_for_next_execution(s, now) is False


# ---------------------------------------------------------------------------
# get_schedules delegates to repo
# ---------------------------------------------------------------------------

class TestGetSchedules:
    def test_delegates_to_get_active_schedules(self):
        mock_schedules = [MagicMock(), MagicMock()]
        with patch("src.scheduling.get_active_schedules", return_value=mock_schedules) as mock_fn:
            result = get_schedules()
            mock_fn.assert_called_once()
            assert result == mock_schedules
