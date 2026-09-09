# ─────────────────────────────────────────────────────────────────────────────
# inputs.py  –  All user-facing input and validation
# ─────────────────────────────────────────────────────────────────────────────
# Every function here re-prompts on invalid input and never raises to the
# caller.  No business logic lives in this file; no imports from logic.py
# or data.py (keeping this layer independently testable).
# ─────────────────────────────────────────────────────────────────────────────

import re


# ── Internal helper ───────────────────────────────────────────────────────────

def _read(prompt: str) -> str:
    """Thin wrapper around input() so tests can patch it easily."""
    return input(prompt).strip()


# ── Customer identity ─────────────────────────────────────────────────────────

def get_customer_name() -> str:
    """
    Prompt for a customer name.
    Rules:
      • Must be non-empty.
      • Must contain at least one alphabetic character (rejects pure symbols/digits).
    Returns the name with leading/trailing whitespace stripped.
    """
    while True:
        name = _read("  Customer name : ").strip()
        if not name:
            print("  ! Name cannot be empty.")
            continue
        if not re.search(r"[A-Za-z]", name):
            print("  ! Name must contain at least one letter.")
            continue
        return name


# ── Booking type ──────────────────────────────────────────────────────────────

def get_booking_type() -> str:
    """
    Show numbered menu and return 'B' (advance) or 'W' (walk-in).
    """
    print()
    print("  Booking type:")
    print("    1. Advance booking")
    print("    2. Walk-in")
    while True:
        raw = _read("  Select [1/2] : ")
        if raw == "1":
            return "B"
        if raw == "2":
            return "W"
        print("  ! Please enter 1 or 2.")


# ── Station type ──────────────────────────────────────────────────────────────

def get_station_type(rates: dict) -> str:
    """
    Show a numbered list of station types and return the chosen key.
    *rates* is RATES from data.py (dict mapping type-key -> hourly rate),
    passed in so inputs.py stays free of data.py imports.
    """
    # Build ordered list from the rates dict so order matches data.py definition
    options = list(rates.keys())
    print()
    print("  Station type:")
    for i, key in enumerate(options, 1):
        print(f"    {i}. {key}  (Rs {rates[key]}/hr)")
    while True:
        raw = _read(f"  Select [1-{len(options)}] : ")
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print(f"  ! Please enter a number between 1 and {len(options)}.")


# ── Game category ─────────────────────────────────────────────────────────────

def get_game_category(surcharges: dict) -> str:
    """
    Show numbered game-category menu and return 'AAA' or 'STANDARD'.
    *surcharges* is GAME_SURCHARGE from data.py.
    """
    options = list(surcharges.keys())
    print()
    print("  Game category:")
    for i, key in enumerate(options, 1):
        note = f"  (+Rs {surcharges[key]} surcharge)" if surcharges[key] > 0 else "  (no surcharge)"
        print(f"    {i}. {key}{note}")
    while True:
        raw = _read(f"  Select [1-{len(options)}] : ")
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print(f"  ! Please enter a number between 1 and {len(options)}.")


# ── Duration ──────────────────────────────────────────────────────────────────

def get_duration() -> float:
    """
    Prompt for expected session duration in hours.
    Rules:
      • Must be numeric (rejects text, symbols, malformed decimals like '1.5.0').
      • Must be strictly positive.
      • Max 12 hours (one operating day).
    Returns duration as a float (hours).
    """
    while True:
        raw = _read("  Duration (hours, e.g. 1.5) : ")
        # Guard against malformed decimals with more than one dot
        if raw.count(".") > 1:
            print("  ! Invalid duration.")
            continue
        try:
            value = float(raw)
        except ValueError:
            print("  ! Invalid duration. Enter a positive number (e.g. 1 or 1.5).")
            continue
        if value <= 0:
            print("  ! Duration must be greater than zero.")
            continue
        if value > 12:
            print("  ! Maximum session duration is 12 hours.")
            continue
        return value


# ── Player count ──────────────────────────────────────────────────────────────

def get_player_count() -> int:
    """
    Prompt for number of players.
    Rules:
      • Must be a whole positive integer (rejects floats, symbols, text).
    """
    while True:
        raw = _read("  Number of players : ")
        # Reject anything with a decimal point
        if "." in raw:
            print("  ! Player count must be a whole number.")
            continue
        try:
            value = int(raw)
        except ValueError:
            print("  ! Invalid player count. Enter a whole positive number.")
            continue
        if value <= 0:
            print("  ! Player count must be at least 1.")
            continue
        return value


# ── Snack order ───────────────────────────────────────────────────────────────

def get_snack_order(menu: dict, menu_labels: dict) -> list[tuple[str, int]]:
    """
    Interactively build a snack order using a numbered menu.
    *menu*        : MENU from data.py  (canonical-key -> price)
    *menu_labels* : MENU_LABELS from data.py (int -> canonical-key)

    Returns a list of (item_name, quantity) tuples in the order they were added.
    Pressing Enter (empty input) ends the order.
    """
    items: list[tuple[str, int]] = []

    print()
    print("  ── Snack menu ──────────────────────────────")
    for num, key in menu_labels.items():
        display = key.title()          # "COLD DRINK" -> "Cold Drink"
        print(f"    {num}. {display:<18} Rs {menu[key]}")
    print("    0. Done — no more items")
    print("  ────────────────────────────────────────────")

    while True:
        raw = _read("  Select item [0 to finish] : ")

        if raw == "0" or raw == "":
            break

        if not raw.isdigit() or int(raw) not in menu_labels:
            print(f"  ! Please enter a number between 0 and {len(menu_labels)}.")
            continue

        item_key = menu_labels[int(raw)]

        # Get quantity
        qty_raw = _read(f"  Quantity of {item_key.title()} : ")
        if "." in qty_raw:
            print("  ! Quantity must be a whole number.")
            continue
        try:
            qty = int(qty_raw)
        except ValueError:
            print("  ! Invalid quantity. Enter a whole positive number.")
            continue
        if qty <= 0:
            print("  ! Quantity must be at least 1.")
            continue

        items.append((item_key, qty))
        print(f"  ✓ Added {qty} × {item_key.title()} (Rs {menu[item_key] * qty})")

    return items


# ── Scheduled start time (for advance bookings) ───────────────────────────────

def get_scheduled_start(open_min: int, close_min: int, current_min: int) -> int:
    """
    Prompt for an HH:MM start time for an advance booking.
    Rules:
      • Must be valid HH:MM format.
      • Must be within café operating hours.
      • Must be at or after the current virtual time.
    Returns time as minutes since midnight.
    """
    while True:
        raw = _read("  Booking start time (HH:MM) : ")
        # Validate format
        if not re.match(r"^\d{1,2}:\d{2}$", raw):
            print("  ! Invalid time format. Use HH:MM (e.g. 14:30).")
            continue
        try:
            h, m = raw.split(":")
            h, m = int(h), int(m)
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
        except ValueError:
            print("  ! Invalid time.")
            continue
        t = h * 60 + m
        if t < open_min or t >= close_min:
            print(f"  ! Time must be within operating hours ({open_min // 60:02d}:00 – {close_min // 60:02d}:00).")
            continue
        if t < current_min:
            print("  ! Booking time is in the past.")
            continue
        return t


# ── Skip-time command ─────────────────────────────────────────────────────────

def get_skip_minutes() -> int:
    """
    Parse the integer minute-value from a 'skip <N>' command.
    Returns the positive integer N, or 0 if the input is invalid
    (caller decides whether to re-prompt).
    """
    raw = _read("  Minutes to skip : ")
    if "." in raw:
        print("  ! Minutes must be a whole number.")
        return 0
    try:
        value = int(raw)
    except ValueError:
        print("  ! Invalid number.")
        return 0
    if value <= 0:
        print("  ! Skip amount must be at least 1 minute.")
        return 0
    if value > 720:
        print("  ! Cannot skip more than 12 hours at once.")
        return 0
    return value