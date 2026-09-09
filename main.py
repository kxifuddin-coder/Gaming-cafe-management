# ─────────────────────────────────────────────────────────────────────────────
# main.py  –  Entry point and session loop
# ─────────────────────────────────────────────────────────────────────────────

from data import (
    RATES, MENU, MENU_LABELS, GAME_SURCHARGE, stations, queues,
    advance_bookings, visit_log, STATION_CAPACITIES, expired_sessions,
    get_time, fmt_time,
    OPEN_HOUR, CLOSE_HOUR,
)
from inputs import (
    get_customer_name, get_booking_type, get_station_type,
    get_game_category, get_duration, get_player_count,
    get_snack_order, get_scheduled_start, get_skip_minutes,
)
from logic import (
    is_cafe_open,
    check_availability, get_available_units, allocate_station, add_to_queue,
    release_station, serve_next_in_queue,
    register_advance_booking, activate_due_bookings,
    skip_time,
    calculate_gaming_charge, calculate_game_surcharge,
    calculate_food_total, apply_loyalty_discount,
    increment_visit_count, print_bill,
)


# ─────────────────────────────────────────────────────────────────────────────
# Display helpers
# ─────────────────────────────────────────────────────────────────────────────

def _header(title: str) -> None:
    print()
    print("  ╔" + "═" * 42 + "╗")
    print(f"  ║  {title:<40}║")
    print("  ╚" + "═" * 42 + "╝")


def display_welcome() -> None:
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║       GAMING CAFÉ  –  BOOKING SYSTEM     ║")
    print("  ╚══════════════════════════════════════════╝")


def display_status() -> None:
    """Show current virtual time and a compact station-availability table."""
    now = get_time()
    print(f"\n  Virtual clock : {fmt_time(now)}")
    print(f"  Café hours    : {OPEN_HOUR:02d}:00 – {CLOSE_HOUR:02d}:00")
    print()
    print(f"  {'Unit':<6} {'Type':<20} {'Status':<12} {'Customer / End'}")
    print("  " + "─" * 58)
    for uid, unit in stations.items():
        status = "OCCUPIED" if unit["occupied"] else "FREE"
        if unit["occupied"] and unit["current_booking"]:
            bk   = unit["current_booking"]
            info = f"{bk['customer_name']}  until {fmt_time(int(unit['session_end']))}"
        else:
            info = "—"
        print(f"  {uid:<6} {unit['type']:<20} {status:<12} {info}")

    # Show queues if any
    any_waiting = any(q for q in queues.values())
    if any_waiting:
        print()
        print("  Waiting queues:")
        for stype, q in queues.items():
            if q:
                print(f"    {stype}: " + ", ".join(q))


def display_main_menu() -> str:
    """
    Show the main action menu and return the chosen option.
    """
    print()
    print("  ── Main menu ──────────────────────────────")
    print("    1. New customer (booking or walk-in)")
    print("    2. End active session & print bill")
    print("    3. Skip time (advance virtual clock)")
    print("    4. Add snacks to active session")
    print("    5. View expired sessions & print bills")
    print("    q. Quit")
    print("  ───────────────────────────────────────────")
    while True:
        choice = input("  Select option : ").strip().lower()
        if choice in ("1", "2", "3", "4", "5", "q"):
            return choice
        print("  ! Please enter 1, 2, 3, 4, 5 or q.")


# ─────────────────────────────────────────────────────────────────────────────
# New customer flow
# ─────────────────────────────────────────────────────────────────────────────

def run_new_customer() -> None:
    """
    Collect inputs for a new customer, check availability, and allocate
    or queue them.  Snack collection and billing happen in end_session().
    """
    now = get_time()

    if not is_cafe_open(now):
        print(f"\n  ! Café is closed. Operating hours: {OPEN_HOUR:02d}:00 – {CLOSE_HOUR:02d}:00.")
        return

    _header("New Customer")

    # ── Core inputs ───────────────────────────────────────────────────────────
    customer_name  = get_customer_name()
    booking_type   = get_booking_type()
    station_type   = get_station_type(RATES)
    game_category  = get_game_category(GAME_SURCHARGE)
    duration_hrs   = get_duration()
    player_count   = get_player_count()
    duration_min   = duration_hrs * 60

    # ── Start time ────────────────────────────────────────────────────────────
    if booking_type == "B":
        scheduled_start = get_scheduled_start(
            open_min    = OPEN_HOUR  * 60,
            close_min   = CLOSE_HOUR * 60,
            current_min = now,
        )
        if scheduled_start + duration_min > CLOSE_HOUR * 60:
            print(f"  ! Session would run past closing time ({CLOSE_HOUR:02d}:00). Reduce duration or book an earlier slot.")
            return
    else:
        scheduled_start = now

    booking = {
        "customer_name":   customer_name,
        "station_type":    station_type,
        "game_category":   game_category,
        "duration_hrs":    duration_hrs,
        "player_count":    player_count,
        "scheduled_start": scheduled_start,
        "snacks":          [],
    }

    import math
    # ── Availability check ────────────────────────────────────────────────────
    capacity = STATION_CAPACITIES.get(station_type, 4)
    units_needed = math.ceil(player_count / capacity)
    available_units = get_available_units(station_type, scheduled_start, duration_min)

    units_to_book = 0

    if player_count > capacity:
        if len(available_units) >= units_needed:
            print(f"\n  ! {station_type} supports only {capacity} people per unit.")
            print(f"  {len(available_units)} units are available. You need {units_needed} units.")
            while True:
                ans = input(f"  [B]ook {units_needed} units, [W]ait in queue, or [C]ancel? ").strip().upper()
                if ans in ("B", "W", "C"): break
            if ans == "B":
                units_to_book = units_needed
            elif ans == "W":
                position = add_to_queue(customer_name, station_type)
                print(f"  {customer_name} added to the waiting queue — position {position}.")
                return
            else:
                return
        elif len(available_units) > 0:
            print(f"\n  ! {station_type} supports only {capacity} people per unit.")
            print(f"  Only {len(available_units)} unit(s) available.")
            max_people = len(available_units) * capacity
            while True:
                ans = input(f"  [P]roceed with {len(available_units)} unit(s) for {max_people} people, [W]ait in queue, or [C]ancel? ").strip().upper()
                if ans in ("P", "W", "C"): break
            if ans == "P":
                units_to_book = len(available_units)
                booking["player_count"] = max_people
            elif ans == "W":
                position = add_to_queue(customer_name, station_type)
                print(f"  {customer_name} added to the waiting queue — position {position}.")
                return
            else:
                return
        else:
            print(f"\n  ! No {station_type} available right now.")
            while True:
                ans = input("  [W]ait in queue or [C]ancel? ").strip().upper()
                if ans in ("W", "C"): break
            if ans == "W":
                position = add_to_queue(customer_name, station_type)
                print(f"  {customer_name} added to the waiting queue — position {position}.")
            return
    else:
        if len(available_units) >= 1:
            units_to_book = 1
        else:
            print(f"\n  ! No {station_type} available right now.")
            position = add_to_queue(customer_name, station_type)
            print(f"  {customer_name} added to the waiting queue — position {position}.")
            return

    # ── Allocate ──────────────────────────────────────────────────────────────
    for uid in available_units[:units_to_book]:
        b = dict(booking)
        b["snacks"] = []
        allocate_station(uid, b)
        if booking_type == "B":
            register_advance_booking(b)
            print(f"  ✓ Advance booking confirmed: {customer_name} → {station_type} unit {uid}")
        else:
            print(f"  ✓ Walk-in allocated: {customer_name} → {station_type} unit {uid}")

    if booking_type != "B":
        print(f"  Start : {fmt_time(scheduled_start)}   End : {fmt_time(int(scheduled_start + duration_min))}")
        print(f"  (Use option 2 from the main menu when the customer finishes playing.)")
    else:
        print(f"  Start : {fmt_time(scheduled_start)}   End : {fmt_time(int(scheduled_start + duration_min))}")


# ─────────────────────────────────────────────────────────────────────────────
# End session flow
# ─────────────────────────────────────────────────────────────────────────────

def _select_occupied_unit() -> int | None:
    """Show all currently occupied units and let the operator pick one by number."""
    occupied = {uid: unit for uid, unit in stations.items() if unit["occupied"]}
    if not occupied:
        print("\n  ! No sessions are currently active.")
        return None

    print()
    print("  Active sessions:")
    uid_list = list(occupied.keys())
    for i, uid in enumerate(uid_list, 1):
        unit = occupied[uid]
        bk   = unit["current_booking"]
        cust = bk["customer_name"] if bk else "Unknown"
        end  = fmt_time(int(unit["session_end"])) if unit["session_end"] else "?"
        print(f"    {i}. Unit {uid}  |  {unit['type']:<20} |  {cust}  (until {end})")

    while True:
        raw = input(f"  Select session [1-{len(uid_list)}] : ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(uid_list):
            return uid_list[int(raw) - 1]
        print(f"  ! Please enter a number between 1 and {len(uid_list)}.")


def end_session() -> None:
    """
    Operator manually ends an active session:
    select unit → add snacks → compute bill → print → free station.
    """
    _header("End Session")

    unit_id = _select_occupied_unit()
    if unit_id is None:
        return

    unit    = stations[unit_id]
    bk      = unit["current_booking"]
    now     = get_time()

    customer_name  = bk["customer_name"]
    station_type   = bk["station_type"]
    game_category  = bk["game_category"]
    session_start  = unit["session_start"]
    session_end    = unit["session_end"]

    # Actual duration: use min(now, declared_end) so we don't overbill
    actual_end_min = min(now, session_end) if session_end else now
    actual_dur_min = max(1.0, actual_end_min - session_start)

    print(f"\n  Ending session for {customer_name} on {station_type} unit {unit_id}.")
    print(f"  Actual duration: {int(actual_dur_min // 60)}h {int(actual_dur_min % 60):02d}m")

    # Snack order
    print()
    print("  Add snacks / drinks to the customer's tab:")
    new_snacks = get_snack_order(MENU, MENU_LABELS)
    food_items = bk.get("snacks", []) + new_snacks

    # Billing
    gaming_charge = calculate_gaming_charge(station_type, actual_dur_min)
    surcharge     = calculate_game_surcharge(game_category)
    food_total    = calculate_food_total(food_items)
    subtotal      = gaming_charge + surcharge + food_total

    discounted    = apply_loyalty_discount(customer_name, subtotal)
    discount_amt  = subtotal - discounted
    final_total   = discounted

    increment_visit_count(customer_name)
    release_station(unit_id)

    print_bill(
        customer_name  = customer_name,
        station_type   = station_type,
        duration_min   = actual_dur_min,
        gaming_charge  = gaming_charge,
        surcharge      = surcharge,
        food_items     = food_items,
        food_total     = food_total,
        discount       = discount_amt,
        final_total    = final_total,
    )

    visits_now = visit_log.get(customer_name.upper(), 0)
    remaining  = max(0, 5 - visits_now)
    if remaining > 0:
        print(f"  ℹ  {customer_name} has {visits_now} visit(s). {remaining} more to unlock loyalty discount.")
    else:
        print(f"  ℹ  {customer_name} is a loyalty member ({visits_now} visits). 10% discount applied.")


def add_snacks_to_session() -> None:
    _header("Add Snacks")
    unit_id = _select_occupied_unit()
    if unit_id is None:
        return

    unit = stations[unit_id]
    bk = unit["current_booking"]
    print(f"\n  Adding snacks for {bk['customer_name']} on {unit['type']} unit {unit_id}.")

    new_snacks = get_snack_order(MENU, MENU_LABELS)
    if new_snacks:
        bk.setdefault("snacks", []).extend(new_snacks)
        print("  ✓ Snacks added to session.")

def bill_expired_session() -> None:
    _header("Expired Sessions")
    if not expired_sessions:
        print("\n  ! No expired sessions to bill.")
        return

    print()
    print("  Expired sessions:")
    for i, bk in enumerate(expired_sessions, 1):
        cust = bk["customer_name"]
        uid = bk["unit_id"]
        stype = bk["station_type"]
        end = fmt_time(int(bk["session_end"]))
        print(f"    {i}. Unit {uid} | {stype:<16} | {cust} (ended at {end})")

    while True:
        raw = input(f"  Select session to bill [1-{len(expired_sessions)}] : ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(expired_sessions):
            idx = int(raw) - 1
            break
        print(f"  ! Please enter a number between 1 and {len(expired_sessions)}.")

    bk = expired_sessions.pop(idx)
    customer_name = bk["customer_name"]
    station_type = bk["station_type"]
    game_category = bk["game_category"]
    actual_dur_min = bk["actual_dur_min"]

    print(f"\n  Billing expired session for {customer_name} on {station_type} unit {bk['unit_id']}.")

    print()
    print("  Add any final snacks / drinks before checkout:")
    new_snacks = get_snack_order(MENU, MENU_LABELS)
    food_items = bk.get("snacks", []) + new_snacks

    gaming_charge = calculate_gaming_charge(station_type, actual_dur_min)
    surcharge     = calculate_game_surcharge(game_category)
    food_total    = calculate_food_total(food_items)
    subtotal      = gaming_charge + surcharge + food_total

    discounted    = apply_loyalty_discount(customer_name, subtotal)
    discount_amt  = subtotal - discounted
    final_total   = discounted

    increment_visit_count(customer_name)

    print_bill(
        customer_name  = customer_name,
        station_type   = station_type,
        duration_min   = actual_dur_min,
        gaming_charge  = gaming_charge,
        surcharge      = surcharge,
        food_items     = food_items,
        food_total     = food_total,
        discount       = discount_amt,
        final_total    = final_total,
    )

    visits_now = visit_log.get(customer_name.upper(), 0)
    remaining  = max(0, 5 - visits_now)
    if remaining > 0:
        print(f"  ℹ  {customer_name} has {visits_now} visit(s). {remaining} more to unlock loyalty discount.")
    else:
        print(f"  ℹ  {customer_name} is a loyalty member ({visits_now} visits). 10% discount applied.")


# ─────────────────────────────────────────────────────────────────────────────
# Skip-time flow
# ─────────────────────────────────────────────────────────────────────────────

def handle_skip_time() -> None:
    now = get_time()
    print(f"\n  Current time: {fmt_time(now)}")
    minutes = get_skip_minutes()
    if minutes > 0:
        new_time = now + minutes
        if new_time >= CLOSE_HOUR * 60:
            print(f"  ! That would advance past closing time ({CLOSE_HOUR:02d}:00). Capping at closing time.")
            minutes = CLOSE_HOUR * 60 - now
        if minutes > 0:
            skip_time(minutes)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    display_welcome()

    while True:
        display_status()
        choice = display_main_menu()

        if choice == "1":
            run_new_customer()
        elif choice == "2":
            end_session()
        elif choice == "3":
            handle_skip_time()
        elif choice == "4":
            add_snacks_to_session()
        elif choice == "5":
            bill_expired_session()
        elif choice == "q":
            print()
            print("  Session ended. Goodbye!")
            print()
            break


if __name__ == "__main__":
    main()