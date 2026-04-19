"""
Determine whether the next schedule has been reached.
"""

from datetime import datetime
from typing import List
from .repo import Schedule, get_active_schedules, upsert_schedule


def get_schedules() -> List[Schedule]:
    return get_active_schedules()


def is_ready_for_next_execution(schedule: Schedule, now: datetime) -> bool:
    if schedule.last_execution is None:
        match schedule.schedule:
            case "1D":
                return now.hour == 0
            case "4H":
                return now.hour % 4 == 0
            case "1H":
                return now.minute == 0
            case "1M":
                return now.second < 30
            case default:
                return False
    else:
        last_execution = datetime.fromisoformat(schedule.last_execution)
        match schedule.schedule:
            case "1W":
                return now.isocalendar()[1] != last_execution.isocalendar()[1] and now.weekday() == 0 and now.hour == 0
            case "1D":
                return now.day != last_execution.day and now.hour == 0
            case "4H":
                return now.hour % 4 == 0 and now.hour != last_execution.hour
            case "1H":
                return now.minute == 0 and now.hour != last_execution.hour
            case "1M":
                return now.second < 30 and now.minute != last_execution.minute
            case default:
                return now.hour != last_execution.hour

def register_execution(schedule: Schedule, now: datetime) -> None:
    schedule.last_execution = now.isoformat()
    repo.upsert_schedule(schedule)

def update_schedule(schedule: Schedule) -> None:
    repo.upsert_schedule(schedule)