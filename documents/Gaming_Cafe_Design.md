<br/>**Gaming Café Booking  
and Billing System**

_Software Design Document_

# 1\. Design Overview

The application is a modular terminal program with four Python modules. data.py holds configuration and shared in-memory state; inputs.py provides interactive input helpers; logic.py implements domain operations; main.py coordinates menus and workflows. The current implementation does not strictly enforce this boundary: main.py imports and mutates data state directly, computes group allocation details, and reads some inputs directly.

# 2\. Terminology and Formulae

- Station type: PS3, PS4, PS5, Racing Simulator, or Arcade.
- Unit: one physical console/setup identified by unit ID.
- Advance booking: a scheduled reservation checked against overlapping intervals.
- Walk-in: a customer requesting a session starting at the current virtual time.
- Queue: ordered list of customer names for a station type; the current data model stores names only, so it cannot reliably preserve all booking details.
- Group: multiple physical units associated with one customer booking through a shared group_id.

Required billing formula: charge = ceil(hourly_rate × elapsed_minutes / 60), using integer elapsed minutes and a documented currency-rounding policy for discounts. Avoid floating-point duration multiplication.

# 3\. Architecture

| **Module** | **Actual role and boundary**                                                                                                                             |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| data.py    | Constants, labels/catalogue, mutable shared dictionaries/lists, virtual clock helpers.                                                                   |
| inputs.py  | Booking, station, game, duration, player count, snack and skip-time prompts.                                                                             |
| logic.py   | Availability, allocation/release, booking activation, charge calculation, discounts, receipts and time operations.                                       |
| main.py    | Menu dispatch and orchestration; currently imports data directly, mutates state, computes units_needed/player split/group_id, and uses input() directly. |

Architecture rule: the data.py header currently says main.py must not import it, but the implementation violates that rule. Choose and enforce one contract. Recommended target: main.py orchestrates via logic.py and input helpers; logic.py owns state mutation; data.py exports configuration/state only.

# 4\. State Model

| **Concept**      | **Current representation**                   | **Design implication**                                                                                                                         |
| ---------------- | -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Unit status      | Station dictionary with free/occupied fields | There is no RESERVED station state; advance reservations are checked by interval overlap.                                                      |
| Queue            | queues: dict\[str, list\[str\]\]             | Only names are stored; consider queue records containing name, requested station/game, player count, duration, arrival order and booking type. |
| Advance bookings | List of booking dictionaries                 | Display reservations as a separate upcoming-bookings view, not as a fictitious station state.                                                  |
| Expired sessions | List of billable session records             | Expiry should not imply billing has happened; retain records until settled.                                                                    |
| Loyalty          | Customer key → accumulated hours             | Group hours must be credited once using the chosen group duration rule.                                                                        |

# 5\. Menu Option 2

Menu option 2 opens a submenu with three operations: end an active session, remove a customer from a queue, and cancel an advance booking. The PRD, function inventory, and tests must include all three. Each branch should validate the target, report success/failure, and leave state consistent.

# 6\. Availability and Allocation

1. Check whether a unit is occupied for the requested interval.
2. Check advance-booking intervals for overlap with the requested start/end.
3. Before allocating a new walk-in, check whether an older eligible queued customer has priority.
4. After successful allocation of a queued customer, remove the matching queue entry.
5. Release should update unit state; the actual reservation protection is provided by overlap checking, not by a "held" flag printed by release_station.

# 7\. Queue Algorithm

Target FIFO behavior: (1) enqueue a structured request with an arrival sequence; (2) when capacity becomes available, inspect the oldest eligible request; (3) confirm the requested interval does not conflict with a reservation; (4) allocate it; (5) remove it from the queue only after successful allocation; (6) if it cannot be served, continue to the next eligible request only under a documented fairness rule. serve_next_in_queue is currently an empty stub and must not be documented as operational.

# 8\. Advance Booking Lifecycle

When virtual time advances from T1 to T2, process all bookings with start times in (T1, T2\] in chronological order. A booking crossed by a skip must activate with an effective start time no earlier than the current virtual time, unless the product intentionally models late arrival and records lateness separately. A booking whose start equals the current time should be activated immediately after registration or by an explicit activation call.

Cancellation must remove or mark the booking cancelled so it no longer blocks availability. Upcoming reservations must be visible in a separate reservation list.

# 9\. Billing and Rounding

Use integer elapsed minutes. For a Rs 100/hour rate and 66 minutes, ceil(100 × 66 / 60) = Rs 110. Do not compute from binary floating-point hours such as 1.1 × 60. Define discount rounding explicitly; recommended policy is conventional half-up rounding to the nearest whole rupee, implemented with Decimal or integer arithmetic rather than Python round(), which uses ties-to-even.

The current print_bill signature accepts a surcharge parameter and prints "Game surcharge Rs 0". The current catalogue prices by game and player tier and does not define an extra AAA/Standard surcharge. Remove the obsolete parameter and receipt line, or explicitly label it as a zero-value legacy field until removed.

# 10\. Loyalty Design

Determine discount eligibility using loyalty hours before the current checkout credit is added, if the policy is intended to reward customers on a later bill after reaching 10 hours. Store a boolean such as discount_applied and base receipt messaging on it. For a group, aggregate the group session duration and credit it once; individual unit checkout must not unintentionally sum or duplicate group hours.

# 11\. Duration and Skip-Time Validation

Duration validation must reject non-finite numeric values, including NaN and infinity, as well as zero, negative values, and values beyond the supported limit. Skip-time validation must return a distinct valid/invalid/cancelled result rather than silently converting invalid input to zero. The caller should retry or show an explicit cancellation message.

# 12\. Virtual Clock and Closing Algorithm

1. Validate the requested skip increment.
2. Compute the target virtual time, capped at 22:00.
3. Process booking starts crossed by the interval in chronological order.
4. Expire sessions whose end time is reached, preserving billable details.
5. At 22:00, close active sessions under the defined closing policy and retain every unbilled session for checkout.
6. Credit loyalty hours exactly once when the bill/session is finalized.
7. Reset the new-day clock and operational station/queue/booking state only after ensuring unbilled records are preserved.

The 22:00 cap currently lives in main.py, although the previous design placed it in the clock algorithm. Move the cap into a single clock/logic operation or update the module boundary so implementation and diagram agree. The virtual clock is the only operational clock; no automatic wall-clock expiry exists.

# 13\. Session and Checkout Functions

end_session and bill_expired_session contain near-duplicate checkout logic. Refactor to a shared checkout routine that accepts active or expired session records, aggregates group units where appropriate, computes gaming/food totals, applies the discount policy, prints one consistent receipt, and records loyalty credit once.

# 14\. Function Inventory

| **Function / area**      | **Responsibility / status**                                                                       |
| ------------------------ | ------------------------------------------------------------------------------------------------- |
| is_cafe_open             | Checks whether the café is within operating hours; include in the function inventory.             |
| check_availability       | Checks occupied state and overlapping booking intervals; remove unused imports where appropriate. |
| allocate_station         | Allocates a free eligible unit; comments should refer to game_name, not game_category.            |
| release_station          | Updates unit state; does not itself reserve a unit against future bookings.                       |
| add_to_queue             | Adds a waiting customer; target implementation should store structured request details.           |
| serve_next_in_queue      | Currently an empty stub; implement FIFO serving and queue cleanup.                                |
| register_advance_booking | Stores a scheduled reservation and associated group/unit details.                                 |
| cancel_advance_booking   | Menu operation; cancel the reservation and unblock its time interval.                             |
| remove_from_queue        | Menu operation; remove the selected customer/request and report outcome.                          |
| activate_due_bookings    | Activate due bookings when time is advanced and handle skipped-over starts.                       |
| calculate_gaming_charge  | Calculate charge from integer minutes and the applicable game/player tier.                        |
| apply_loyalty_discount   | Apply defined threshold and rounding policy; return whether a discount was applied.               |
| print_bill               | Print consistent receipt; remove the obsolete zero-surcharge line.                                |
| start_new_day            | Reset operational state without deleting unbilled expired sessions or loyalty history.            |

# 15\. Target State Transitions

| **Event**                  | **Unit/session result**                                  | **Reservation/queue result**                                   |
| -------------------------- | -------------------------------------------------------- | -------------------------------------------------------------- |
| Walk-in allocated          | FREE → OCCUPIED                                          | Remove from queue if previously queued.                        |
| Session reaches end        | OCCUPIED → FREE; retain expired bill record until billed | Serve eligible queue in FIFO order.                            |
| Advance booking registered | No RESERVED unit status in current model                 | Add booking interval to reservation list.                      |
| Advance booking cancelled  | No unit state change unless already activated            | Remove/mark cancelled; interval no longer blocks availability. |
| Queue removal              | No unit state change                                     | Delete matching queued request.                                |
| Day closes                 | Active sessions become closed/billable records           | Do not erase unbilled records.                                 |

# 16\. Error Handling

- Invalid numeric input receives a clear message and a retry/cancel path.
- Unknown customer or missing queue/booking target is reported without corrupting state.
- A booking conflict returns a clear unavailable result.
- Billing uses deterministic integer-minute arithmetic and explicit rounding.
- Closing/reset operations preserve billable data.

# 17\. Design Verification Matrix

| **Test ID** | **Scenario**           | **Expected result**                                                          |
| ----------- | ---------------------- | ---------------------------------------------------------------------------- |
| DT-01       | Option 2 submenu       | Each submenu route reaches the correct handler.                              |
| DT-02       | Queue removal          | Removed request no longer appears or gets allocated.                         |
| DT-03       | Cancellation           | Cancelled reservation stops blocking availability.                           |
| DT-04       | FIFO                   | Older eligible queued request is served before a new walk-in.                |
| DT-05       | Queue cleanup          | Successful allocation removes queue entry.                                   |
| DT-06       | Empty queue stub       | serve_next_in_queue has a tested implementation, not pass.                   |
| DT-07       | NaN/infinity           | Duration rejects non-finite values.                                          |
| DT-08       | Walk-in close boundary | A walk-in cannot silently overrun closing.                                   |
| DT-09       | Closing preservation   | All sessions are billed or retained as billable; loyalty credit occurs once. |
| DT-10       | Billing precision      | 100 Rs/hour × 66 minutes produces Rs 110.                                    |
| DT-11       | Discount rounding      | 105 and 125 subtotals follow the explicit rounding policy.                   |
| DT-12       | Discount message       | Receipt reflects actual discount eligibility before credit.                  |
| DT-13       | Late activation        | Skipping past a booking start creates a consistent start/end state.          |
| DT-14       | Current-time booking   | Booking at now activates without waiting for an unrelated future skip.       |
| DT-15       | Group loyalty          | Group duration is credited once, even with unit-by-unit checkout.            |
| DT-16       | Reservation display    | Upcoming reservations are visible separately from station occupancy.         |
| DT-17       | Reset safety           | Unbilled expired sessions survive new-day reset.                             |

# 18\. Current Limitations and Future Work

Known gaps from the code audit: queue serving is an empty stub; FIFO is not enforced against new walk-ins; allocated customers may remain in the queue; advance bookings may be queued; queue entries store names only; reservation visibility is incomplete; invalid skip input silently returns zero; NaN can pass duration validation; billing uses floating-point arithmetic; discount rounding uses Python round(); loyalty messaging can be misleading; skipped-over bookings can activate late; same-time bookings wait for skip_time; group loyalty can be duplicated on separate checkout; closing can lose unbilled revenue; and main.py violates the documented data.py import boundary.

Potential future work: persistent storage, structured queue tickets, one checkout service, test automation, and an optional real-time clock mode. These are recommendations, not existing features.

# 19\. Pseudocode Algorithms for Every Function

This section documents the control flow of every function defined in the current repository's data.py, inputs.py, logic.py, and main.py. The pseudocode describes current behavior unless a subheading explicitly says Target Design. Known implementation gaps are labelled rather than presented as completed features.

## 19.1 data.py — State and time helpers

### data.py — get_time()

**Purpose:** Return the current virtual clock in minutes since midnight.

```
START
RETURN the current value stored in virtual_clock[0]
END
```

### data.py — set_time()

**Purpose:** Set the virtual clock to a supplied minute value.

```
START
SET virtual_clock[0] = minutes
END
```

### data.py — advance_time()

**Purpose:** Move the virtual clock forward by a number of minutes.

```
START
ADD delta to virtual_clock[0]
END
```

### data.py — fmt_time()

**Purpose:** Convert minutes since midnight into HH:MM display text.

```
START
hours = minutes DIV 60
remaining_minutes = minutes MOD 60
RETURN hours and remaining_minutes formatted as two digits each
END
```

### data.py — parse_time()

**Purpose:** Convert a valid HH:MM string into minutes since midnight.

```
START
TRIM input and split it at ':'
IF there are not exactly two parts, RAISE ValueError
CONVERT both parts to integers hours and minutes
IF hours is outside 0..23 OR minutes is outside 0..59, RAISE ValueError
RETURN hours * 60 + minutes
END
```

## 19.2 inputs.py — Input collection and validation

### inputs.py — \_read()

**Purpose:** Read a terminal response and remove surrounding whitespace.

```
START
READ input using the supplied prompt
TRIM surrounding whitespace
RETURN the cleaned text
END
```

### inputs.py — get_customer_name()

**Purpose:** Accept a non-empty customer name containing at least one English letter.

```
START
REPEAT
    name = _read(customer-name prompt)
    IF name is empty, DISPLAY error and continue
    IF name contains no A-Z or a-z character, DISPLAY error and continue
    RETURN name
END REPEAT
```

### inputs.py — get_booking_type()

**Purpose:** Return B for advance booking or W for walk-in.

```
START
DISPLAY booking-type options
REPEAT
    READ choice
    IF choice is 1, RETURN B
    IF choice is 2, RETURN W
    OTHERWISE DISPLAY validation message
END REPEAT
```

### inputs.py — get_station_type()

**Purpose:** Return a valid station type selected from the catalogue.

```
START
DISPLAY station types with numbered options
REPEAT
    READ choice
    IF choice is an integer within the displayed range, RETURN matching station type
    OTHERWISE DISPLAY validation message
END REPEAT
```

### inputs.py — get_game_choice()

**Purpose:** Return a game name belonging to the selected station type.

```
START
GET games for the selected station type
DISPLAY each game and its player-tier prices
REPEAT
    READ choice
    IF choice is a valid displayed index, RETURN matching game name
    OTHERWISE DISPLAY validation message
END REPEAT
```

### inputs.py — get_duration()

**Purpose:** Read a positive session duration up to 12 hours.

**Status:** Current code accepts NaN because it does not explicitly reject non-finite values; this is a known defect.

```
START
REPEAT
    READ duration text
    IF text contains more than one decimal point, DISPLAY error and continue
    TRY converting text to a number; IF conversion fails, DISPLAY error and continue
    IF duration <= 0 OR duration > 12, DISPLAY relevant error and continue
    RETURN duration
END REPEAT
```

### inputs.py — get_player_count()

**Purpose:** Accept a whole positive integer number of players.

```
START
REPEAT
    READ player-count text
    IF text contains a decimal point, DISPLAY error and continue
    TRY converting text to integer; IF conversion fails, DISPLAY error and continue
    IF count <= 0, DISPLAY error and continue
    RETURN count
END REPEAT
```

### inputs.py — get_snack_order()

**Purpose:** Build a list of snack-name and quantity pairs.

```
START
INITIALISE items as an empty list
DISPLAY snack menu and prices
REPEAT
    READ item choice
    IF choice is blank or 0, EXIT loop
    IF choice is not a valid menu number, DISPLAY error and continue
    READ quantity
    IF quantity is not a whole positive integer, DISPLAY error and continue
    APPEND (item name, quantity) to items
    DISPLAY line cost
END REPEAT
RETURN items
END
```

### inputs.py — get_scheduled_start()

**Purpose:** Read a valid advance-booking start time within operating hours and not earlier than now.

```
START
REPEAT
    READ time text in HH:MM format
    IF format is invalid, DISPLAY error and continue
    PARSE hour and minute; IF values are out of range, DISPLAY error and continue
    CONVERT to minutes since midnight
    IF time is before opening or at/after closing, DISPLAY error and continue
    IF time is earlier than current virtual time, DISPLAY error and continue
    RETURN time in minutes
END REPEAT
```

### inputs.py — get_skip_minutes()

**Purpose:** Parse a positive integer skip-time amount.

**Status:** Invalid input currently returns 0; the caller returns to the menu rather than re-prompting.

```
START
READ minutes text
IF text contains a decimal point, DISPLAY error and RETURN 0
TRY converting text to integer; IF conversion fails, DISPLAY error and RETURN 0
IF value <= 0 OR value > 720, DISPLAY error and RETURN 0
RETURN value
END
```

## 19.3 logic.py — Business rules and state transitions

### logic.py — is_cafe_open()

**Purpose:** Check whether a minute-of-day value is within opening and closing boundaries.

```
START
IF OPEN_HOUR * 60 <= time_min < CLOSE_HOUR * 60, RETURN True
OTHERWISE RETURN False
END
```

### logic.py — get_available_units()

**Purpose:** Find station units of the requested type without an overlapping active session or advance booking.

```
START
end_min = start_min + duration_min
INITIALISE available as an empty list
FOR each unit:
    IF unit type differs from requested type, continue
    SET overlap = False
    IF unit is occupied, compare requested interval with its session interval
    FOR each advance booking assigned to this unit:
        CALCULATE booking end time
        IF intervals overlap, SET overlap = True and stop checking bookings
    IF overlap is False, APPEND unit ID to available
RETURN available
END
```

### logic.py — \_upcoming_booking()

**Purpose:** Find the earliest booking for a unit due within a small time window.

```
START
now = get_time()
FOR each sorted advance booking:
    IF booking unit matches AND now <= booking start <= now + within_minutes, RETURN booking
RETURN None
END
```

### logic.py — allocate_station()

**Purpose:** Mark a unit occupied and attach its booking details.

```
START
GET station record for unit_id
SET occupied = True
STORE booking as current_booking
SET session_start = booking scheduled_start
SET session_end = scheduled_start + duration_hrs * 60
END
```

### logic.py — release_station()

**Purpose:** Clear the active booking fields for a unit and notify the operator about a nearby booking or waiting queue.

**Status:** The function prints a queue notice but does not automatically allocate the next customer.

```
START
GET unit and its station type
SET occupied = False
CLEAR current_booking, session_start, and session_end
IF an advance booking starts within 30 minutes, DISPLAY reservation notice and RETURN
IF queue for this station type is non-empty, DISPLAY the next waiting name
END
```

### logic.py — add_to_queue()

**Purpose:** Append a customer name to the selected station-type queue.

```
START
IF station type has no queue, CREATE an empty queue
APPEND customer_name to that queue
RETURN the queue length as the 1-based position
END
```

### logic.py — register_advance_booking()

**Purpose:** Store a confirmed advance booking and keep reservations ordered by start time.

```
START
APPEND booking to advance_bookings
SORT advance_bookings by scheduled_start in ascending order
END
```

### logic.py — activate_due_bookings()

**Purpose:** Activate reservations whose start time has arrived according to the virtual clock.

**Status:** A booking skipped over can be allocated with its old scheduled start; late activation needs correction.

```
START
now = get_time()
INITIALISE still_pending as an empty list
FOR each advance booking:
    IF scheduled_start <= now:
        IF assigned unit exists and is free, allocate the unit and notify operator
        OTHERWISE keep booking in still_pending
    ELSE keep booking in still_pending
REPLACE advance_bookings with still_pending
END
```

### logic.py — skip_time()

**Purpose:** Advance the virtual clock, preserve expired session details, release units, and activate due bookings.

**Status:** Current code depends on caller-side closing-time capping and does not itself settle bills at closing.

```
START
ADVANCE virtual clock by requested minutes
DISPLAY new virtual time
FOR each occupied unit whose session_end <= current time:
    COPY booking details and actual duration into an expired-session record
    APPEND record to expired_sessions
    RELEASE the station
CALL activate_due_bookings
END
```

### logic.py — calculate_gaming_charge()

**Purpose:** Calculate the game charge using the selected game and player-count price tier.

**Status:** The current implementation accepts float minutes; integer-minute arithmetic is the recommended target.

```
START
LOOK UP game information using station_type and game_name
GET pricing dictionary
IF player_count exists as a pricing tier, use its rate
OTHERWISE use the highest available pricing tier
charge = CEILING(rate * duration_minutes / 60)
RETURN charge
END
```

### logic.py — calculate_food_total()

**Purpose:** Calculate the total price for all snack quantities.

```
START
total = 0
FOR each (item_name, quantity) in items:
    total = total + MENU[item_name] * quantity
RETURN total
END
```

### logic.py — apply_loyalty_discount()

**Purpose:** Apply a 10% discount if previously accumulated loyalty hours are at least 10.

**Status:** Python round() uses ties-to-even for exact half values; a documented currency-rounding rule is recommended.

```
START
LOOK UP loyalty hours using uppercase customer name; default to 0
IF hours >= 10, RETURN round(subtotal * 0.90)
OTHERWISE RETURN subtotal
END
```

### logic.py — add_loyalty_hours()

**Purpose:** Add the completed session duration to a customer's loyalty total.

```
START
key = uppercase customer name
SET loyalty_hours[key] = existing hours (or 0) + duration_hrs
END
```

### logic.py — print_bill()

**Purpose:** Display an itemised terminal receipt.

**Status:** The current function prints a zero surcharge line even though current catalogue pricing has no surcharge rule.

```
START
CONVERT duration minutes into hours and remaining minutes
DISPLAY receipt heading, customer, station, and duration
DISPLAY gaming charge
DISPLAY surcharge line according to current function parameters
IF food items exist, display each item quantity and line total, then food total
CALCULATE subtotal = gaming charge + surcharge + food total
DISPLAY subtotal and discount when discount > 0
DISPLAY final amount due
END
```

### logic.py — start_new_day()

**Purpose:** Reset daily station, queue, reservation, expired-session, and clock state.

**Status:** Current code clears expired_sessions; this can discard unpaid bills. Preserve unsettled records before resetting.

```
START
FOR each unit, mark it free and clear its booking/start/end fields
CLEAR every queue
CLEAR advance bookings
CLEAR expired_sessions
SET virtual clock to opening time
END
```

### Target Design — Queue serving (not implemented)

serve_next_in_queue() — planned algorithm, not a function currently implemented in logic.py.

```
START
GET the oldest queue request for the station type
IF queue is empty, RETURN
CHECK whether a unit is available for the requested interval
IF no eligible unit is available, leave request in queue and RETURN
ALLOCATE the selected unit to the oldest eligible request
REMOVE the request from the queue only after allocation succeeds
CONTINUE while free units and eligible queued requests remain
END
```

## 19.4 main.py — Display and workflow functions

### main.py — \_header()

**Purpose:** Display a framed heading for a terminal section.

```
START
PRINT blank line and top border
PRINT title inside the frame
PRINT bottom border
END
```

### main.py — display_welcome()

**Purpose:** Show the application's welcome banner.

```
START
PRINT the Gaming Café Booking System banner
END
```

### main.py — display_status()

**Purpose:** Show virtual time, operating hours, station occupancy, and non-empty queues.

**Status:** Upcoming advance bookings are not shown in the current status display.

```
START
GET current virtual time and display it with café hours
FOR each station unit, display unit ID, type, FREE/OCCUPIED status, and current customer/end time
IF any queue is non-empty, display each station type and its waiting names
END
```

### main.py — display_main_menu()

**Purpose:** Display menu choices and return a valid operator selection.

```
START
DISPLAY available actions
REPEAT
    READ and normalize choice
    IF choice is 1, 2, 3, 4, 5, or q, RETURN choice
    OTHERWISE DISPLAY validation message
END REPEAT
```

### main.py — run_new_customer()

**Purpose:** Collect booking details, check availability, and create an advance booking, walk-in session, or queue entry.

**Status:** Current code does not enforce FIFO queue priority before a new walk-in takes a free unit.

```
START
IF café is closed, DISPLAY message and RETURN
COLLECT customer name, booking type, station type, game, duration, and player count
IF advance booking, collect scheduled start and reject sessions ending after closing; OTHERWISE use current virtual time
GET game capacity and calculate units_needed = CEILING(total_players / capacity)
GET available units for the requested interval
IF enough units exist, determine whether to book, queue, or cancel when multiple units are needed
IF no unit exists, offer queue or cancellation
CREATE group_id and split players across required units
FOR each selected unit, create booking record with snacks empty
IF advance booking, register it; OTHERWISE allocate unit immediately
DISPLAY session start/end details
END
```

### main.py — \_select_occupied_unit()

**Purpose:** Let the operator choose an active session by its displayed number.

```
START
BUILD a collection of occupied units
IF none are occupied, DISPLAY message and RETURN None
DISPLAY occupied units and customer/end-time details
REPEAT until a valid numeric selection is entered
RETURN the corresponding unit ID
END
```

### main.py — remove_from_queue()

**Purpose:** Remove a selected customer name from a selected non-empty queue.

```
START
FIND station-type queues that are not empty
IF no queues are active, DISPLAY message and RETURN
DISPLAY active queue types and request operator selection
VALIDATE station-type selection
DISPLAY names in that queue and request customer index
VALIDATE customer index
REMOVE the selected name from the queue
DISPLAY confirmation
END
```

### main.py — cancel_advance_booking()

**Purpose:** Cancel a selected advance booking and optionally cancel its entire group.

```
START
IF no advance bookings exist, DISPLAY message and RETURN
DISPLAY scheduled bookings
ASK operator to select a booking or cancel the operation
VALIDATE selection
GET selected booking and its group_id
IF related group bookings exist, ask whether to cancel the entire group
REMOVE selected booking and any group bookings approved for cancellation
DISPLAY number of bookings cancelled
END
```

### main.py — handle_option_2()

**Purpose:** Route menu option 2 to session checkout, queue removal, or booking cancellation.

```
START
DISPLAY the three submenu choices
REPEAT
    READ choice
    IF 1, CALL end_session and EXIT loop
    IF 2, CALL remove_from_queue and EXIT loop
    IF 3, CALL cancel_advance_booking and EXIT loop
    OTHERWISE DISPLAY validation message
END REPEAT
```

### main.py — end_session()

**Purpose:** Manually check out an active session or a selected group, calculate charges, print a receipt, and release units.

**Status:** Current code can display '10% discount applied' based on updated loyalty hours even when the current bill did not receive the discount.

```
START
SELECT an occupied unit; IF none, RETURN
GET booking, customer, current virtual time, and group_id
IF other active units share the group_id, ask whether to check out the group together
COLLECT any final snack order
INITIALISE gaming total, food items, and maximum session duration
FOR each unit being checked out:
    CALCULATE elapsed duration up to current time/session end
    ADD game/player-tier charge and saved snacks
    TRACK maximum duration and station types
    RELEASE the unit
CALCULATE food total and subtotal
APPLY loyalty discount using previously accumulated hours
ADD the group's maximum duration to loyalty hours
PRINT itemised receipt and loyalty status message
END
```

### main.py — add_snacks_to_session()

**Purpose:** Append additional snack items to an active session's saved order.

```
START
SELECT an occupied unit; IF none, RETURN
GET its current booking
COLLECT snack order
IF order is not empty, append items to booking snacks and confirm
END
```

### main.py — bill_expired_session()

**Purpose:** Select an expired session, optionally combine its group, calculate charges, and print the bill.

**Status:** Current code removes the selected record before billing; an interruption can lose the unbilled record.

```
START
IF expired_sessions is empty, DISPLAY message and RETURN
DISPLAY expired sessions and request a valid selection
REMOVE selected record from expired_sessions
IF it belongs to a group, ask whether to include related expired records
COLLECT any final snack order
FOR each record being billed, add its gaming charge and saved snacks; track maximum duration
CALCULATE food total, subtotal, loyalty discount, and final amount
ADD group duration to loyalty hours
PRINT itemised receipt and loyalty status message
END
```

### main.py — handle_skip_time()

**Purpose:** Read a virtual-time increment and cap it at closing time before advancing.

```
START
DISPLAY current virtual time
READ skip minutes using get_skip_minutes
IF minutes <= 0, RETURN
IF current time + minutes reaches or passes closing, replace increment with minutes remaining until closing
IF increment > 0, CALL logic.skip_time(increment)
END
```

### main.py — main()

**Purpose:** Run the terminal application loop and dispatch menu actions.

**Status:** The current closing message says active/expired sessions and queues will be erased; this risks losing unbilled records.

```
START
DISPLAY welcome banner
REPEAT
    IF virtual time has reached closing:
        DISPLAY closing message
        ASK operator to quit or start a new day
        IF quit, EXIT loop; OTHERWISE CALL start_new_day and continue
    DISPLAY current status
    GET a valid main-menu choice
    DISPATCH choice to new customer, option-2 submenu, skip time, add snacks, expired billing, or quit
UNTIL operator quits
END
```

## 19.5 Function coverage and implementation notes

The pseudocode covers every function defined in the current four Python modules, including private helpers prefixed with an underscore. The design document also refers to check_availability as a conceptual area; the current repository function that performs this check is get_available_units(). serve_next_in_queue() is documented separately as a target algorithm because the current function body is an empty stub or is absent from the current repository version.

Pseudocode describes logic and is not executable Python. The document update does not modify the GitHub source code. Known defects remain implementation work, including NaN duration validation, FIFO queue serving/cleanup, late booking activation, closing-time billing preservation, currency rounding, and accurate loyalty messaging.