# ─────────────────────────────────────────────────────────────────────────────
# logic.py  –  Business logic and calculations
# ─────────────────────────────────────────────────────────────────────────────
# All state changes go through this file.  Imports from data.py only.
# No input() calls live here.
# ─────────────────────────────────────────────────────────────────────────────

import math
from data import (
    stations, queues, advance_bookings, loyalty_hours,
   MENU, expired_sessions,
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

def get_available_units(station_type: str, start_min: int, duration_min: float) -> list[int]:
    """
    Find all free units of *station_type* for the window [start_min, start_min + duration_min].
    Returns a list of unit_ids that are free.
    """
    end_min = start_min + duration_min
    available = []
    for uid, unit in stations.items():
        if unit["type"] != station_type:
            continue
            
        overlap = False
        if unit["occupied"]:
            s = unit["session_start"]
            e = unit["session_end"]
            if s is None or e is None:
                overlap = True
            elif not (start_min >= e or end_min <= s):
                overlap = True
                
        # Check advance bookings for this unit
        for bk in advance_bookings:
            if bk.get("unit_id") == uid:
                bk_s = bk["scheduled_start"]
                bk_e = bk_s + bk["duration_hrs"] * 60
                if not (start_min >= bk_e or end_min <= bk_s):
                    overlap = True
                    break
                    
        if not overlap:
            available.append(uid)
    return available




# ─────────────────────────────────────────────────────────────────────────────
# 3.  Booking priority check
# ─────────────────────────────────────────────────────────────────────────────

def _upcoming_booking(unit_id: int, within_minutes: int = 30) -> dict | None:
    """
    Return the earliest advance booking for *unit_id* due to start
    within *within_minutes* of the current virtual clock, or None.
    advance_bookings is kept sorted by scheduled_start ascending.
    """
    now = get_time()
    for bk in advance_bookings:
        if bk.get("unit_id") == unit_id and now <= bk["scheduled_start"] <= now + within_minutes:
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
    Free *unit_id*. After clearing, notify if there is an upcoming queue.
    We do NOT automatically start the clock for queued customers anymore.
    """
    unit = stations[unit_id]
    station_type = unit["type"]
    unit["occupied"]        = False
    unit["current_booking"] = None
    unit["session_start"]   = None
    unit["session_end"]     = None

    upcoming = _upcoming_booking(unit_id, within_minutes=30)
    if upcoming:
        print(f"\n  ℹ Unit {unit_id} is reserved for advance booking: {upcoming['customer_name']}.")
        return

    if queues.get(station_type):
        next_customer = queues[station_type][0]
        print(f"\n  ► Unit {unit_id} ({station_type}) is now free. Queue next: {next_customer}. Operator should confirm and allocate from main menu.")


def add_to_queue(customer_name: str, station_type: str) -> int:
    """
    Append *customer_name* to the FIFO queue for *station_type*.
    Returns the 1-based queue position.
    """
    if station_type not in queues:
        queues[station_type] = []
    queues[station_type].append(customer_name)
    return len(queues[station_type])





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
            uid = bk.get("unit_id")
            unit = stations.get(uid)
            if unit and not unit["occupied"]:
                allocate_station(uid, bk)
                print(f"\n  ► Advance booking auto-started: {bk['customer_name']} → {bk['station_type']} unit {uid} at {fmt_time(bk['scheduled_start'])}.")
            else:
                # Still occupied by previous session? Leave it pending to start later
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
            if bk:
                customer = bk["customer_name"]
                duration_actual = unit["session_end"] - unit["session_start"]
                end_str = fmt_time(int(unit["session_end"]))
                utype   = unit["type"]
                print(f"\n  ⏰ Session auto-closed: {customer} on {utype} unit {uid}  (ended {end_str}).")
                
                exp_bk = dict(bk)
                exp_bk["unit_id"] = uid
                exp_bk["actual_dur_min"] = duration_actual
                exp_bk["session_start"] = unit["session_start"]
                exp_bk["session_end"] = unit["session_end"]
                expired_sessions.append(exp_bk)
            release_station(uid)

    # Activate advance bookings that are now due
    activate_due_bookings()


# ─────────────────────────────────────────────────────────────────────────────
# 7.  Billing calculations
# ─────────────────────────────────────────────────────────────────────────────

def calculate_gaming_charge(station_type: str, game_name: str, player_count: int, duration_minutes: float) -> float:
    """
    Gaming charge = hourly_rate × (duration_minutes / 60), rounded up.
    The hourly_rate depends on the game and the number of players.
    """
    from data import GAMES_CATALOG
    
    game_info = GAMES_CATALOG[station_type][game_name]
    pricing = game_info["pricing"]
    
    if player_count in pricing:
        rate = pricing[player_count]
    else:
        max_tier = max(pricing.keys())
        rate = pricing[max_tier]
        
    return math.ceil(rate * (duration_minutes / 60))


def calculate_food_total(items: list[tuple[str, int]]) -> float:
    """Return sum of (unit_price × quantity) for all items."""
    return sum(MENU[name] * qty for name, qty in items)


def apply_loyalty_discount(customer_name: str, subtotal: float) -> float:
    """
    Apply 10% loyalty discount if the customer has >= 10 hours played.
    Returns the discounted total rounded to the nearest rupee.
    """
    hours = loyalty_hours.get(customer_name.upper(), 0.0)
    if hours >= 10.0:
        return round(subtotal * 0.90)
    return subtotal


def add_loyalty_hours(customer_name: str, duration_hrs: float) -> None:
    """Add hours to the customer's loyalty total."""
    key = customer_name.upper()
    loyalty_hours[key] = loyalty_hours.get(key, 0.0) + duration_hrs


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

# ─────────────────────────────────────────────────────────────────────────────
# 9.  End of Day / New Day
# ─────────────────────────────────────────────────────────────────────────────

def start_new_day() -> None:
    """Reset all daily tracking data and reset the virtual clock to opening time."""
    # Stations
    for uid, unit in stations.items():
        unit["occupied"] = False
        unit["current_booking"] = None
        unit["session_start"] = None
        unit["session_end"] = None

    # Queues
    for k in queues.keys():
        queues[k].clear()

    # Lists
    advance_bookings.clear()
    expired_sessions.clear()

    # Clock
    set_time(OPEN_HOUR * 60)
