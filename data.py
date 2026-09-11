# ─────────────────────────────────────────────────────────────────────────────
# data.py  –  Static data and shared in-memory state
# ─────────────────────────────────────────────────────────────────────────────
# All persistent state lives here.  logic.py imports from this module;
# main.py and inputs.py must NOT import from here directly.
# ─────────────────────────────────────────────────────────────────────────────

# ── Café operating hours ──────────────────────────────────────────────────────
OPEN_HOUR  = 10   # 10:00
CLOSE_HOUR = 22   # 22:00

# ── Station type display labels (for menus) ───────────────────────────────────
STATION_LABELS: dict[int, str] = {
    1: "PS3",
    2: "PS4",
    3: "PS5",
    4: "RACING SIMULATOR",
    5: "ARCADE",
}

# ── Dynamic Pricing & Game Catalog ────────────────────────────────────────────
# Structure:
# STATION_TYPE -> Game Name -> { type, max_players, pricing }
# pricing maps player_count to hourly rate in Rs.
GAMES_CATALOG: dict[str, dict[str, dict]] = {
    "PS5": {
        "EA FC 24": {
            "type": "Premium",
            "max_players": 4,
            "pricing": {1: 150, 2: 180, 3: 200, 4: 220}
        },
        "Spider-Man 2": {
            "type": "Premium",
            "max_players": 1,
            "pricing": {1: 160}
        },
        "Mortal Kombat 1": {
            "type": "Normal",
            "max_players": 2,
            "pricing": {1: 120, 2: 150}
        },
        "Call of Duty: MW III": {
            "type": "Premium",
            "max_players": 2,
            "pricing": {1: 140, 2: 180}
        },
        "Astro's Playroom": {
            "type": "Normal",
            "max_players": 1,
            "pricing": {1: 100}
        }
    },
    "PS4": {
        "FIFA 23": {
            "type": "Normal",
            "max_players": 4,
            "pricing": {1: 100, 2: 130, 3: 150, 4: 170}
        },
        "God of War": {
            "type": "Premium",
            "max_players": 1,
            "pricing": {1: 120}
        },
        "Tekken 7": {
            "type": "Normal",
            "max_players": 2,
            "pricing": {1: 90, 2: 120}
        },
        "Minecraft": {
            "type": "Normal",
            "max_players": 4,
            "pricing": {1: 80, 2: 110, 3: 130, 4: 150}
        }
    },
    "PS3": {
        "GTA V": {
            "type": "Premium",
            "max_players": 1,
            "pricing": {1: 80}
        },
        "Call of Duty: BO2": {
            "type": "Normal",
            "max_players": 4,
            "pricing": {1: 60, 2: 80, 3: 100, 4: 120}
        },
        "Blur": {
            "type": "Normal",
            "max_players": 4,
            "pricing": {1: 60, 2: 80, 3: 100, 4: 120}
        }
    },
    "RACING SIMULATOR": {
        "Gran Turismo 7": {
            "type": "Premium",
            "max_players": 1,
            "pricing": {1: 200}
        },
        "F1 23": {
            "type": "Premium",
            "max_players": 1,
            "pricing": {1: 220}
        },
        "Dirt Rally 2.0": {
            "type": "Normal",
            "max_players": 1,
            "pricing": {1: 150}
        }
    },
    "ARCADE": {
        "Street Fighter II": {
            "type": "Normal",
            "max_players": 2,
            "pricing": {1: 50, 2: 80}
        },
        "Pac-Man": {
            "type": "Normal",
            "max_players": 2,
            "pricing": {1: 40, 2: 60}
        },
        "Metal Slug": {
            "type": "Premium",
            "max_players": 2,
            "pricing": {1: 60, 2: 90}
        }
    }
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
queues: dict[str, list[str]] = {key: [] for key in GAMES_CATALOG}

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