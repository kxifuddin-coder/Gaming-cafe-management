# ─────────────────────────────────────────────────────────────────────────────
# logic.py  –  Business logic and calculations
# ─────────────────────────────────────────────────────────────────────────────
# All state changes go through this file.  Imports from data.py only.
# No input() calls live here.
# ─────────────────────────────────────────────────────────────────────────────

import math
from data import (
    stations, queues, advance_bookings, visit_log,
    RATES, MENU, GAME_SURCHARGE,
    get_time, set_time, advance_time, fmt_time,
    OPEN_HOUR, CLOSE_HOUR,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Operating-hours check
# ─────────────────────────────────────────────────────────────────────────────

def is_cafe_open(time_min: int) -> bool:
    """Return True if *time_min* (minutes since midnight) is within operating hours."""
    return OPEN_HOUR * 60 <= time_min < CLOSE_HOUR * 60


# ─────────────────────────────────────────────────────────────────────────────
# 2.  Station availability
# ─────────────────────────────────────────────────────────────────────────────

def check_availability(station_type: str, start_min: int, duration_min: float) -> int | None:
    """
    Find a free unit of *station_type* for the window [start_min, start_min + duration_min].
    Returns the unit_id of the first free unit found, or None if all are occupied.
    """
    end_min = start_min + duration_min
    for uid, unit in stations.items():
        if unit["type"] != station_type:
            continue
        if not unit["occupied"]:
            return uid
        # Occupied: check whether its current session overlaps our window
        s = unit["session_start"]
        e = unit["session_end"]
        if s is None or e is None:
            # Indefinite occupation (walk-in with no declared end) — treat as busy
            continue
        # No overlap if our window starts at or after the unit's end,
        # or our window ends at or before the unit's start
        if start_min >= e or end_min <= s:
            return uid   # Free during our window
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Booking priority check
# ─────────────────────────────────────────────────────────────────────────────

def _upcoming_booking(station_type: str, within_minutes: int = 30) -> dict | None:
    """
    Return the earliest advance booking for *station_type* due to start
    within *within_minutes* of the current virtual clock, or None.
    advance_bookings is kept sorted by scheduled_start ascending.
    """
    now = get_time()
    for bk in advance_bookings:
        if bk["station_type"] != station_type:
            continue
        if now <= bk["scheduled_start"] <= now + within_minutes:
            return bk
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 4.  Allocate / release stations
# ─────────────────────────────────────────────────────────────────────────────

def allocate_station(unit_id: int, booking: dict) -> None:
    """
    Mark *unit_id* as occupied and store *booking* against it.
    booking must contain: customer_name, station_type, game_category,
                          duration_hrs, player_count, scheduled_start.
    session_end is set to scheduled_start + duration in minutes.
    """
    unit = stations[unit_id]
    unit["occupied"]        = True
    unit["current_booking"] = booking
    unit["session_start"]   = booking["scheduled_start"]
    unit["session_end"]     = booking["scheduled_start"] + booking["duration_hrs"] * 60


def release_station(unit_id: int) -> None:
    """
    Free *unit_id*.  After clearing, honour advance-booking priority:
    if an advance booking is due within 30 minutes for this station type,
    hold the unit for it.  Otherwise hand it to the next walk-in in the queue.
    """
    unit = stations[unit_id]
    station_type = unit["type"]
    unit["occupied"]        = False
    unit["current_booking"] = None
    unit["session_start"]   = None
    unit["session_end"]     = None

    # Check priority: advance booking due within 30 minutes?
    upcoming = _upcoming_booking(station_type, within_minutes=30)
    if upcoming:
        # Hold the unit — do not hand it to walk-ins
        return

    # No priority booking — serve next walk-in if one is waiting
    if queues.get(station_type):
        next_customer = queues[station_type].pop(0)
        walk_in_booking = {
            "customer_name":    next_customer,
            "station_type":     station_type,
            "game_category":    "STANDARD",   # walk-in default; will be updated by run_session
            "duration_hrs":     1.0,           # placeholder; real duration tracked by virtual clock
            "player_count":     1,
            "scheduled_start":  get_time(),
        }
        allocate_station(unit_id, walk_in_booking)
        print(f"\n  ► Queue: {next_customer} has been moved from the waiting queue to {station_type} unit {unit_id}.")


def add_to_queue(customer_name: str, station_type: str) -> int:
    """
    Append *customer_name* to the FIFO queue for *station_type*.
    Returns the 1-based queue position.
    """
    if station_type not in queues:
        queues[station_type] = []
    queues[station_type].append(customer_name)
    return len(queues[station_type])


def serve_next_in_queue(station_type: str) -> None:
    """
    If a unit of *station_type* is free and the queue is non-empty
    (and no advance booking is imminent), allocate it to the next walk-in.
    """
    if not queues.get(station_type):
        return
    upcoming = _upcoming_booking(station_type, within_minutes=30)
    if upcoming:
        return
    for uid, unit in stations.items():
        if unit["type"] == station_type and not unit["occupied"]:
            release_station(uid)   # release_station handles queue dequeue
            return


# ─────────────────────────────────────────────────────────────────────────────
# 5.  Advance-booking management
# ─────────────────────────────────────────────────────────────────────────────

def register_advance_booking(booking: dict) -> None:
    """Add a confirmed advance booking and keep the list sorted by start time."""
    advance_bookings.append(booking)
    advance_bookings.sort(key=lambda b: b["scheduled_start"])


def activate_due_bookings() -> None:
    """
    Called after the virtual clock is advanced.
    Move any advance bookings whose scheduled_start <= now into active station slots.
    """
    now = get_time()
    still_pending = []
    for bk in advance_bookings:
        if bk["scheduled_start"] <= now:
            uid = check_availability(bk["station_type"], bk["scheduled_start"], bk["duration_hrs"] * 60)
            if uid is not None:
                allocate_station(uid, bk)
                print(f"\n  ► Advance booking activated: {bk['customer_name']} → {bk['station_type']} unit {uid} at {fmt_time(bk['scheduled_start'])}.")
            else:
                # No unit available (shouldn't happen if booked correctly, but guard anyway)
                still_pending.append(bk)
        else:
            still_pending.append(bk)
    advance_bookings[:] = still_pending


# ─────────────────────────────────────────────────────────────────────────────
# 6.  Virtual-clock skip and session auto-close
# ─────────────────────────────────────────────────────────────────────────────

def skip_time(minutes: int) -> None:
    """
    Advance virtual clock by *minutes*.
    After advancing:
      1. Close any sessions whose session_end <= new time.
      2. Activate any pending advance bookings whose start <= new time.
    """
    advance_time(minutes)
    now = get_time()
    print(f"\n  ⏱  Clock → {fmt_time(now)}")

    # Auto-close expired sessions
    for uid, unit in stations.items():
        if unit["occupied"] and unit["session_end"] is not None and unit["session_end"] <= now:
            bk = unit["current_booking"]
            customer = bk["customer_name"] if bk else "Unknown"
            duration_actual = unit["session_end"] - unit["session_start"]
            end_str = fmt_time(int(unit["session_end"]))
            utype   = unit["type"]
            print(f"\n  ⏰ Session auto-closed: {customer} on {utype} unit {uid}  (ended {end_str}).")
            release_station(uid)

    # Activate advance bookings that are now due
    activate_due_bookings()


# ─────────────────────────────────────────────────────────────────────────────
# 7.  Billing calculations
# ─────────────────────────────────────────────────────────────────────────────

def calculate_gaming_charge(station_type: str, duration_minutes: float) -> float:
    """
    Gaming charge = hourly_rate × (duration_minutes / 60), rounded up.
    Raises KeyError if station_type is not in RATES.
    """
    rate = RATES[station_type]
    return math.ceil(rate * (duration_minutes / 60))


def calculate_game_surcharge(game_category: str) -> float:
    """Return Rs 100 for AAA, Rs 0 for STANDARD."""
    return GAME_SURCHARGE.get(game_category.upper(), 0)


def calculate_food_total(items: list[tuple[str, int]]) -> float:
    """Return sum of (unit_price × quantity) for all items."""
    return sum(MENU[name] * qty for name, qty in items)


def apply_loyalty_discount(customer_name: str, subtotal: float) -> float:
    """
    Apply 10% loyalty discount if the customer has ≥ 5 completed visits.
    Returns the discounted total rounded to the nearest rupee.
    """
    visits = visit_log.get(customer_name.upper(), 0)
    if visits >= 5:
        return round(subtotal * 0.90)
    return subtotal


def increment_visit_count(customer_name: str) -> None:
    """Increment completed-visit counter.  Creates the entry at 0 if new."""
    key = customer_name.upper()
    visit_log[key] = visit_log.get(key, 0) + 1


# ─────────────────────────────────────────────────────────────────────────────
# 8.  Bill printing
# ─────────────────────────────────────────────────────────────────────────────

def print_bill(
    customer_name:  str,
    station_type:   str,
    duration_min:   float,
    gaming_charge:  float,
    surcharge:      float,
    food_items:     list[tuple[str, int]],
    food_total:     float,
    discount:       float,
    final_total:    float,
) -> None:
    """Print the complete itemised bill to the terminal."""
    hours, mins = divmod(int(duration_min), 60)
    dur_str = f"{hours}h {mins:02d}m"

    W = 38   # receipt width
    SEP = "─" * W

    print()
    print("  " + "═" * W)
    print(f"  {'FINAL BILL':^{W}}")
    print("  " + "═" * W)
    print(f"  Customer  : {customer_name}")
    print(f"  Station   : {station_type}")
    print(f"  Duration  : {dur_str}")
    print("  " + SEP)
    print(f"  {'Gaming charge':<22} Rs {gaming_charge:>6.0f}")
    if surcharge > 0:
        print(f"  {'Game surcharge (AAA)':<22} Rs {surcharge:>6.0f}")
    else:
        print(f"  {'Game surcharge':<22} Rs {'0':>6}")

    if food_items:
        print("  " + SEP)
        print("  Snacks:")
        for name, qty in food_items:
            display = name.title()
            line_total = MENU[name] * qty
            print(f"    {qty} × {display:<18} Rs {line_total:>5}")
        print(f"  {'Food total':<22} Rs {food_total:>6.0f}")

    subtotal = gaming_charge + surcharge + food_total
    print("  " + SEP)
    print(f"  {'Subtotal':<22} Rs {subtotal:>6.0f}")

    if discount > 0:
        print(f"  {'Loyalty discount (10%)':<22} Rs {discount:>6.0f}")

    print("  " + SEP)
    print(f"  {'TOTAL DUE':<22} Rs {final_total:>6.0f}")
    print("  " + "═" * W)
    print()
