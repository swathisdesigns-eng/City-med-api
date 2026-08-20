from datetime import datetime, date, time, timedelta

DAY_MAP = {0: "mon", 1: "tue", 2: "wed",
           3: "thu", 4: "fri", 5: "sat", 6: "sun"}

WINDOWS = {
    "morning": (time(9, 0), time(11, 0)),
    "afternoon": (time(13, 0), time(15, 30)),
    "evening": (time(17, 0), time(18, 0)),
}


def generate_day_slots(slot_duration_minutes: int, time_pref: str = "any"):
    """Generate slot start times for one day based on clinic windows."""
    windows = [WINDOWS[time_pref]] if time_pref in WINDOWS else list(
        WINDOWS.values())
    slots = []
    for start, end in windows:
        current = datetime.combine(date.today(), start)
        end_dt = datetime.combine(date.today(), end)
        while current < end_dt:
            slots.append(current.time())
            current += timedelta(minutes=slot_duration_minutes)
    return slots
