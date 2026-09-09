# ─────────────────────────────────────────────────────────────────────────────
# data.py  –  Static data and shared in-memory state
# ─────────────────────────────────────────────────────────────────────────────
# All persistent state lives here.  logic.py imports from this module;
# main.py and inputs.py must NOT import from here directly.
# ─────────────────────────────────────────────────────────────────────────────

# ── Café operating hours ──────────────────────────────────────────────────────
OPEN_HOUR  = 10   # 10:00
CLOSE_HOUR = 22   # 22:00

# ── Hourly rates (Rs) per station type ───────────────────────────────────────
RATES: dict[str, int] = {
    "PS3":              50,
    "PS4":              70,
    "PS5":             100,
    "RACING SIMULATOR": 120,
    "ARCADE":           60,
}

# ── Station type display labels (for menus) ───────────────────────────────────
STATION_LABELS: dict[int, str] = {
    1: "PS3",
    2: "PS4",
    3: "PS5",
    4: "RACING SIMULATOR",
    5: "ARCADE",
}

# ── Station max capacities ────────────────────────────────────────────────────
STATION_CAPACITIES: dict[str, int] = {
    "PS3": 4,
    "PS4": 4,
    "PS5": 4,
    "RACING SIMULATOR": 1,
    "ARCADE": 2,
}

# ── Snack / drink menu (Rs) ───────────────────────────────────────────────────
MENU: dict[str, int] = {
    "COLD DRINK": 40,
    "CHIPS":      30,
    "COFFEE":     50,
    "SANDWICH":   80,
}

# ── Menu display labels (for numbered selection) ──────────────────────────────
MENU_LABELS: dict[int, str] = {
    1: "COLD DRINK",
    2: "CHIPS",
    3: "COFFEE",
    4: "SANDWICH",
}

# ── Game-category surcharge ───────────────────────────────────────────────────
GAME_SURCHARGE: dict[str, int] = {
    "AAA":      100,
    "STANDARD":   0,
}

GAME_CATEGORY_LABELS: dict[int, str] = {
    1: "AAA",
    2: "STANDARD",
}

# ── Physical station units ────────────────────────────────────────────────────
# Each unit is tracked independently.
# Structure:
#   unit_id (int) -> {
#       "type"            : str,         station type key
#       "occupied"        : bool,
#       "current_booking" : dict | None, see booking structure below
#       "session_start"   : float | None virtual-minutes since midnight
#       "session_end"     : float | None expected end (for advance bookings)
#   }
#
# Booking dict fields:
#   customer_name, station_type, game_category, duration_hrs,
#   player_count, scheduled_start (virtual minutes since midnight)

stations: dict[int, dict] = {
    # PS3 units
    1: {"type": "PS3",              "occupied": False, "current_booking": None, "session_start": None, "session_end": None},
    2: {"type": "PS3",              "occupied": False, "current_booking": None, "session_start": None, "session_end": None},
    # PS4 units
    3: {"type": "PS4",              "occupied": False, "current_booking": None, "session_start": None, "session_end": None},
    4: {"type": "PS4",              "occupied": False, "current_booking": None, "session_start": None, "session_end": None},
    # PS5 units
    5: {"type": "PS5",              "occupied": False, "current_booking": None, "session_start": None, "session_end": None},
    6: {"type": "PS5",              "occupied": False, "current_booking": None, "session_start": None, "session_end": None},
    # Racing Simulator units
    7: {"type": "RACING SIMULATOR", "occupied": False, "current_booking": None, "session_start": None, "session_end": None},
    # Arcade units
    8: {"type": "ARCADE",           "occupied": False, "current_booking": None, "session_start": None, "session_end": None},
    9: {"type": "ARCADE",           "occupied": False, "current_booking": None, "session_start": None, "session_end": None},
}

# ── Walk-in waiting queues ────────────────────────────────────────────────────
# Maps station type -> FIFO list of customer names
queues: dict[str, list[str]] = {key: [] for key in RATES}

# ── Advance bookings not yet started ─────────────────────────────────────────
# List of booking dicts, kept sorted by scheduled_start ascending.
advance_bookings: list[dict] = []

# ── Expired sessions awaiting billing ─────────────────────────────────────────
# List of dicts, each representing an auto-closed session that needs to be billed
expired_sessions: list[dict] = []

# ── Customer loyalty log ──────────────────────────────────────────────────────
# Maps customer name (case-normalised) -> total hours played
loyalty_hours: dict[str, float] = {}

# ── Virtual clock ─────────────────────────────────────────────────────────────
# Time is stored as minutes since midnight so arithmetic is trivial.
# Starts at opening time.
virtual_clock: list[int] = [OPEN_HOUR * 60]   # mutable container so logic.py can update it

def get_time() -> int:
    """Return current virtual time as minutes since midnight."""
    return virtual_clock[0]

def set_time(minutes: int) -> None:
    """Set virtual clock to *minutes* since midnight."""
    virtual_clock[0] = minutes

def advance_time(delta: int) -> None:
    """Advance virtual clock by *delta* minutes."""
    virtual_clock[0] += delta

def fmt_time(minutes: int) -> str:
    """Format minutes-since-midnight as HH:MM string."""
    h, m = divmod(minutes, 60)
    return f"{h:02d}:{m:02d}"

def parse_time(hhmm: str) -> int:
    """Parse 'HH:MM' to minutes since midnight.  Raises ValueError on bad input."""
    parts = hhmm.strip().split(":")
    if len(parts) != 2:
        raise ValueError
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError
    return h * 60 + m