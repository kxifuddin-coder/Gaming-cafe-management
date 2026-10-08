# Gaming Cafe Management System

## 📖 Problem Statement

Managing a modern gaming cafe presents unique operational challenges that standard booking software fails to address. Hardware inventory is strictly constrained (e.g., exactly two PS5s, four PS4s) and walk-in customers heavily overlap with advance reservations. Furthermore, pricing models are highly dynamic—charging different rates not just per console, but specifically based on the game played and the number of active players (e.g., 4 players on a single *EA FC 24* session costs more per hour than 1 player on *Spider-Man 2*).

Without a robust system, cafe operators face:
1. **Revenue Leakage**: Miscalculated partial hours, unbilled mid-session snack orders, or incorrect player-count pricing.
2. **Resource Conflicts**: Walk-in customers being seated at consoles that have advance bookings scheduled within their playtime window.
3. **Queue Chaos**: No fair FIFO (First-In-First-Out) isolation for customers waiting for specific console types.
4. **End-of-Day Data Stagnation**: "Runaway tabs" that are never closed and temporary queues leaking into the next business day.

## 🚀 The Solution

This system is a **Corporate-Level Scalable CLI Application** designed specifically for gaming cafes. It acts as a unified POS (Point of Sale), hardware tracker, and booking algorithmic engine. 

### Key Features
* **Dynamic Algorithmic Pricing**: Deep integration with a `GAMES_CATALOG` that calculates precise hourly rates based on the exact game and explicit player-capacity tiers. Automatically distributes large groups mathematically across multiple screens.
* **Smart Availability & Overlap Detection**: Walk-in durations are algorthmically projected against future advance bookings. The system physically prevents an operator from seating a 2-hour walk-in if that unit is reserved 1 hour from now.
* **Isolated Queue Management**: Fair FIFO waitlists strictly isolated by hardware type (PS4 vs. PS5 vs. Racing Simulators).
* **Virtual Operating Clock**: Time is tracked dynamically. Sessions automatically expire the exact minute they conclude and are cleanly pushed to an `expired_sessions` billing queue.
* **Loyalty & Discount Engine**: Strict floating-point boundaries track cumulative playtime for returning customers, unlocking VIP discounts only when exact thresholds (e.g., >= 10.0 hours) are met.
* **Automated Daily Resets**: Seamless End-of-Day flow (22:00 cutoff) that wipes temporary tabs, clears waitlists, and archives sessions, while safely preserving persistent data (loyalty hours).

## 📁 Project Structure

* **`main.py`**: The application entry point. Handles the interactive operator UI, menu loops, and user flows.
* **`logic.py`**: The core algorithmic engine. Handles time projection, availability overlaps, dynamic billing math, and state transitions.
* **`data.py`**: The centralized database / state management. Houses the `GAMES_CATALOG`, physical hardware dictionary (`stations`), and waitlists.
* **`inputs.py`**: Robust input sanitization. Ensures operator data entry cannot crash the backend.
* **`test.py`**: An exhaustive corporate-grade `unittest` suite covering exact float boundaries, array isolation, time projections, and edge cases.

## 🛠️ How to Run

**1. Run the application:**
```bash
python main.py
```
*(Follow the on-screen prompts to manage bookings, skip virtual time, or checkout sessions).*

**2. Run the Unit Tests:**
The codebase is heavily covered by edge-case testing. To verify the integrity of the system:
```bash
# Recommended to install pytest for verbose execution
pip install pytest

# Run the test suite (with UTF-8 encoding for UI emojis)
$env:PYTHONIOENCODING="utf-8"; pytest test.py -v -s
```
