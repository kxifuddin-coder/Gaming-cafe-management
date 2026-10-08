# ─────────────────────────────────────────────────────────────────────────────
# main.py  –  Entry point and session loop
# ─────────────────────────────────────────────────────────────────────────────

from data import (
    GAMES_CATALOG, MENU, MENU_LABELS, stations, queues,
    advance_bookings, loyalty_hours, expired_sessions,
    get_time, fmt_time,
    OPEN_HOUR, CLOSE_HOUR,
)
from inputs import (
    get_customer_name, get_booking_type, get_station_type,
    get_game_choice, get_duration, get_player_count,
    get_snack_order, get_scheduled_start, get_skip_minutes,
)
from logic import (
    is_cafe_open,
    get_available_units, allocate_station, add_to_queue,
    release_station,
    register_advance_booking, activate_due_bookings,
    skip_time,
    calculate_gaming_charge, calculate_food_total, apply_loyalty_discount,
    add_loyalty_hours, print_bill,
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
    print("    2. End session / Remove queue / Cancel booking")
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
    station_type   = get_station_type(GAMES_CATALOG)
    game_choice    = get_game_choice(station_type, GAMES_CATALOG)
    duration_hrs   = get_duration()
    total_players  = get_player_count()
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

    import math
    game_info = GAMES_CATALOG[station_type][game_choice]
    capacity = game_info["max_players"]
    units_needed = math.ceil(total_players / capacity)
    available_units = get_available_units(station_type, scheduled_start, duration_min)

    units_to_book = 0

    if total_players > capacity:
        if len(available_units) >= units_needed:
            print(f"\n  ! {game_choice} supports only {capacity} people per unit.")
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
            print(f"\n  ! {game_choice} supports only {capacity} people per unit.")
            print(f"  Only {len(available_units)} unit(s) available.")
            max_people = len(available_units) * capacity
            while True:
                ans = input(f"  [P]roceed with {len(available_units)} unit(s) for {max_people} people, [W]ait in queue, or [C]ancel? ").strip().upper()
                if ans in ("P", "W", "C"): break
            if ans == "P":
                units_to_book = len(available_units)
                total_players = max_people
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
            while True:
                ans = input("  [W]ait in queue or [C]ancel? ").strip().upper()
                if ans in ("W", "C"): break
            if ans == "W":
                position = add_to_queue(customer_name, station_type)
                print(f"  {customer_name} added to the waiting queue — position {position}.")
            return

    # ── Allocate ──────────────────────────────────────────────────────────────
    import uuid
    group_id = str(uuid.uuid4())
    
    # Split players evenly
    players_per_unit = [total_players // units_to_book + (1 if i < total_players % units_to_book else 0) for i in range(units_to_book)]
    
    for i, uid in enumerate(available_units[:units_to_book]):
        b = {
            "customer_name":   customer_name,
            "station_type":    station_type,
            "game_name":       game_choice,
            "duration_hrs":    duration_hrs,
            "player_count":    players_per_unit[i],
            "scheduled_start": scheduled_start,
            "snacks":          [],
            "unit_id":         uid,
            "group_id":        group_id,
        }
        
        if booking_type == "B":
            register_advance_booking(b)
            print(f"  ✓ Advance booking confirmed: {customer_name} → {station_type} unit {uid} ({b['player_count']}P)")
        else:
            allocate_station(uid, b)
            print(f"  ✓ Walk-in allocated: {customer_name} → {station_type} unit {uid} ({b['player_count']}P)")

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


def remove_from_queue() -> None:
    _header("Remove Customer from Queue")
    
    # Filter queues that have customers
    active_queues = {k: v for k, v in queues.items() if v}
    
    if not active_queues:
        print("\n  ! All waiting queues are currently empty.")
        return
    
    print("\n  Active Queues:")
    queue_keys = list(active_queues.keys())
    for i, stype in enumerate(queue_keys, 1):
        print(f"    {i}. {stype} ({len(active_queues[stype])} waiting)")
    
    while True:
        q_raw = input(f"  Select station type [1-{len(queue_keys)}] : ").strip()
        if q_raw.isdigit() and 1 <= int(q_raw) <= len(queue_keys):
            selected_stype = queue_keys[int(q_raw) - 1]
            break
        print(f"  ! Please enter a number between 1 and {len(queue_keys)}.")
    
    customers = active_queues[selected_stype]
    print(f"\n  Customers waiting for {selected_stype}:")
    for i, cust in enumerate(customers, 1):
        print(f"    {i}. {cust}")
    
    while True:
        c_raw = input(f"  Select customer to remove [1-{len(customers)}] : ").strip()
        if c_raw.isdigit() and 1 <= int(c_raw) <= len(customers):
            idx = int(c_raw) - 1
            break
        print(f"  ! Please enter a number between 1 and {len(customers)}.")
    
    removed = queues[selected_stype].pop(idx)
    print(f"\n  ✓ Removed '{removed}' from the {selected_stype} queue.")

def cancel_advance_booking() -> None:
    _header("Cancel Advance Booking")
    if not advance_bookings:
        print("\n  ! No advance bookings currently scheduled.")
        return

    print("\n  Scheduled Advance Bookings:")
    for i, bk in enumerate(advance_bookings, 1):
        cust = bk["customer_name"]
        uid = bk["unit_id"]
        stype = bk["station_type"]
        start = fmt_time(int(bk["scheduled_start"]))
        print(f"    {i}. Unit {uid} | {stype:<16} | {cust} (starts at {start})")

    while True:
        raw = input(f"  Select booking to cancel [1-{len(advance_bookings)}] (or [C]ancel) : ").strip().upper()
        if raw == "C":
            return
        if raw.isdigit() and 1 <= int(raw) <= len(advance_bookings):
            idx = int(raw) - 1
            break
        print(f"  ! Please enter a number between 1 and {len(advance_bookings)} or 'C'.")

    bk_to_cancel = advance_bookings[idx]
    group_id = bk_to_cancel.get("group_id")
    
    bks_to_remove = [bk_to_cancel]
    
    if group_id:
        group_bks = [b for b in advance_bookings if b.get("group_id") == group_id and b != bk_to_cancel]
        if group_bks:
            ans = input(f"  This booking is part of a group ({len(group_bks) + 1} units). Cancel entire group? [Y/N] : ").strip().upper()
            if ans == "Y":
                bks_to_remove.extend(group_bks)
                
    for b in bks_to_remove:
        advance_bookings.remove(b)
        
    print(f"\n  ✓ Successfully canceled {len(bks_to_remove)} advance booking(s) for {bk_to_cancel['customer_name']}.")

def handle_option_2() -> None:
    _header("Manage Sessions / Queues / Bookings")
    print("  1. End active session")
    print("  2. Remove customer from queue")
    print("  3. Cancel advance booking")
    while True:
        ans = input("  Select [1-3] : ").strip()
        if ans == "1":
            end_session()
            break
        elif ans == "2":
            remove_from_queue()
            break
        elif ans == "3":
            cancel_advance_booking()
            break
        else:
            print("  ! Invalid option. Please enter 1, 2, or 3.")

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
    group_id = bk.get("group_id")

    units_to_checkout = [unit_id]
    if group_id:
        active_group_units = [u for u, un in stations.items() if un["occupied"] and un["current_booking"] and un["current_booking"].get("group_id") == group_id]
        if len(active_group_units) > 1:
            ans = input(f"  This unit is part of a group ({len(active_group_units)} active units). Checkout entire group together? [Y/N] : ").strip().upper()
            if ans == "Y":
                units_to_checkout = active_group_units

    customer_name = bk["customer_name"]
    print(f"\n  Ending session for {customer_name} ({len(units_to_checkout)} unit(s)).")

    # Snack order
    print()
    print("  Add snacks / drinks to the group's tab:")
    new_snacks = get_snack_order(MENU, MENU_LABELS)

    total_gaming_charge = 0.0
    all_food_items = list(new_snacks)
    max_dur_min = 0.0
    
    station_types = set()

    for uid in units_to_checkout:
        u = stations[uid]
        b = u["current_booking"]
        actual_end_min = min(now, u["session_end"]) if u["session_end"] else now
        actual_dur_min = max(1.0, actual_end_min - u["session_start"])
        max_dur_min = max(max_dur_min, actual_dur_min)
        station_types.add(b["station_type"])

        total_gaming_charge += calculate_gaming_charge(b["station_type"], b["game_name"], b["player_count"], actual_dur_min)
        all_food_items.extend(b.get("snacks", []))

        release_station(uid)

    food_total = calculate_food_total(all_food_items)
    subtotal = total_gaming_charge + food_total

    discounted = apply_loyalty_discount(customer_name, subtotal)
    discount_amt = subtotal - discounted
    final_total = discounted

    # Add max duration of this group session as hours played
    add_loyalty_hours(customer_name, max_dur_min / 60.0)

    station_type_str = list(station_types)[0] if len(station_types) == 1 else "Multiple Units"

    print_bill(
        customer_name  = customer_name,
        station_type   = station_type_str,
        duration_min   = max_dur_min,
        gaming_charge  = total_gaming_charge,
        surcharge      = 0.0,
        food_items     = all_food_items,
        food_total     = food_total,
        discount       = discount_amt,
        final_total    = final_total,
    )

    from data import loyalty_hours
    hours_now = loyalty_hours.get(customer_name.upper(), 0.0)
    remaining = max(0.0, 10.0 - hours_now)
    if remaining > 0:
        print(f"  ℹ  {customer_name} has played {hours_now:.1f} hours. {remaining:.1f} more hours to unlock loyalty discount.")
    else:
        print(f"  ℹ  {customer_name} is a loyalty member ({hours_now:.1f} hours). 10% discount applied.")


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
    group_id = bk.get("group_id")

    bks_to_checkout = [bk]
    if group_id:
        group_bks = [b for b in expired_sessions if b.get("group_id") == group_id]
        if len(group_bks) >= 1:
            ans = input(f"  This session is part of a group ({len(group_bks) + 1} expired sessions). Checkout entire group together? [Y/N] : ").strip().upper()
            if ans == "Y":
                bks_to_checkout.extend(group_bks)
                for b in group_bks:
                    expired_sessions.remove(b)

    print(f"\n  Billing expired session for {customer_name} ({len(bks_to_checkout)} unit(s)).")

    print()
    print("  Add any final snacks / drinks before checkout:")
    new_snacks = get_snack_order(MENU, MENU_LABELS)

    total_gaming_charge = 0.0
    all_food_items = list(new_snacks)
    max_dur_min = 0.0
    station_types = set()

    for b in bks_to_checkout:
        actual_dur_min = b["actual_dur_min"]
        max_dur_min = max(max_dur_min, actual_dur_min)
        station_types.add(b["station_type"])

        total_gaming_charge += calculate_gaming_charge(b["station_type"], b["game_name"], b["player_count"], actual_dur_min)
        all_food_items.extend(b.get("snacks", []))

    food_total = calculate_food_total(all_food_items)
    subtotal = total_gaming_charge + food_total

    discounted = apply_loyalty_discount(customer_name, subtotal)
    discount_amt = subtotal - discounted
    final_total = discounted

    # Add max duration of this group session as hours played
    add_loyalty_hours(customer_name, max_dur_min / 60.0)

    station_type_str = list(station_types)[0] if len(station_types) == 1 else "Multiple Units"

    print_bill(
        customer_name  = customer_name,
        station_type   = station_type_str,
        duration_min   = max_dur_min,
        gaming_charge  = total_gaming_charge,
        surcharge      = 0.0,
        food_items     = all_food_items,
        food_total     = food_total,
        discount       = discount_amt,
        final_total    = final_total,
    )

    from data import loyalty_hours
    hours_now = loyalty_hours.get(customer_name.upper(), 0.0)
    remaining = max(0.0, 10.0 - hours_now)
    if remaining > 0:
        print(f"  ℹ  {customer_name} has played {hours_now:.1f} hours. {remaining:.1f} more hours to unlock loyalty discount.")
    else:
        print(f"  ℹ  {customer_name} is a loyalty member ({hours_now:.1f} hours). 10% discount applied.")


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
        if get_time() >= CLOSE_HOUR * 60:
            print("\n" + "═" * 60)
            print("  🌙 THE CAFE HAS REACHED CLOSING TIME (22:00).")
            print("  All active sessions have been forcefully closed.")
            print("  All unbilled expired sessions and queues will be erased.")
            print("═" * 60)
            ans = input("\n  Press Enter to start a new day, or 'q' to quit: ").strip().lower()
            if ans == 'q':
                print("\n  Session ended. Goodbye!\n")
                break
            else:
                from logic import start_new_day
                start_new_day()
                print("\n  🌅 A new day has started. Welcome!\n")
                continue

        display_status()
        choice = display_main_menu()

        if choice == "1":
            run_new_customer()
        elif choice == "2":
            handle_option_2()
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