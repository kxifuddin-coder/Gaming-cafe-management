**Gaming Café Booking and Billing System**

_Product Requirements Document_

# 1\. Product Overview

The Gaming Café Booking and Billing System is a terminal-based Python application for managing gaming-station availability, walk-in and advance bookings, game selection, player capacity, session timing, snacks and drinks, billing, loyalty discounts, queues, and end-of-day reset.

The current repository contains four core Python modules: data.py, inputs.py, logic.py, and main.py. The implementation is intentionally console-based and keeps operational state in memory.

# 2\. Problem Statement

A gaming café must coordinate several station types, multiple physical units, different games, different prices for player counts, advance reservations, walk-ins, session duration, food orders, and customer loyalty. Manual handling can cause double-booking, incorrect pricing, lost snack orders, and inconsistent billing. The system centralizes these operations in a single terminal workflow.

# 3\. Goals and Objectives

- Provide a simple terminal workflow for café operators.
- Track each physical gaming unit independently.
- Support both advance bookings and walk-ins.
- Prevent allocation of units that overlap existing sessions or advance reservations.
- Select games according to the chosen station type.
- Calculate pricing from game and player-count tiers.
- Support groups that require multiple units using a shared group_id.
- Maintain FIFO waiting queues for unavailable station types.
- Allow snacks and drinks to be added during an active session or at checkout.
- Automatically track cumulative loyalty hours and apply a 10% discount at 10 or more hours.
- Support a virtual clock for testing session expiry and advance-booking activation.
- Allow expired sessions to be billed after automatic closure.
- Reset daily operational state at closing while preserving loyalty hours.

# 4\. Product Scope

| **In Scope**                               | **Out of Scope / Not Implemented**   |
| ------------------------------------------ | ------------------------------------ |
| Terminal-based customer/session operations | GUI/web interface                    |
| Station availability and allocation        | Persistent database                  |
| Advance bookings and walk-in queues        | Online customer self-service booking |
| Game catalog and dynamic pricing           | Online payment gateway               |
| Multi-unit group sessions                  | Cloud synchronization                |
| Snack/drink ordering                       | User accounts/authentication         |
| Billing and loyalty discount               | Historical reporting/analytics       |
| Virtual clock and end-of-day reset         | Automated notification service       |

# 5\. Users and Roles

| **User**      | **Responsibilities**                                                                                                                                            |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Café Operator | Enters customer details, creates bookings, allocates stations, adds snacks, ends sessions, bills expired sessions, advances virtual time, and starts a new day. |
| Customer      | Provides name, booking preference, station/game choice, duration, player count, and optional snack orders through the operator.                                 |

# 6\. User Interface

The application runs entirely in a terminal by executing main.py. The main loop displays station status and a numbered operational menu.

- 1\. New customer / booking
- 2\. End active session
- 3\. Skip time
- 4\. Add snacks to active session
- 5\. View expired sessions and print bills
- q. Quit

The interface is input-driven. Invalid entries are rejected and the operator is prompted again.

# 7\. Inputs

| **Input**          | **Rule**                                                      |
| ------------------ | ------------------------------------------------------------- |
| Customer name      | Non-empty and must contain at least one alphabetic character. |
| Booking type       | 1 = Advance booking; 2 = Walk-in.                             |
| Station type       | Selected from PS3, PS4, PS5, Racing Simulator, or Arcade.     |
| Game               | Selected from the catalog for the chosen station type.        |
| Duration           | Positive number of hours; maximum 12 hours.                   |
| Player count       | Positive whole number.                                        |
| Advance start time | HH:MM, within 10:00–22:00 and not in the past.                |
| Snacks/drinks      | Numbered menu selection; positive integer quantity.           |
| Skip time          | Positive whole number of minutes, maximum 720 per action.     |

# 8\. Station and Game Catalog

The current data.py defines nine physical units:

| **Station Type** | **Units** | **Capacity Basis**        |
| ---------------- | --------- | ------------------------- |
| PS3              | 1–2       | Game-specific max_players |
| PS4              | 3–4       | Game-specific max_players |
| PS5              | 5–6       | Game-specific max_players |
| Racing Simulator | 7         | Game-specific max_players |
| Arcade           | 8–9       | Game-specific max_players |

The current catalog contains the following games and player-count hourly pricing:

| **Station**      | **Game**             | **Type** | **Pricing (Rs/hr)**            |
| ---------------- | -------------------- | -------- | ------------------------------ |
| PS5              | EA FC 24             | Premium  | 1P 150; 2P 180; 3P 200; 4P 220 |
| PS5              | Spider-Man 2         | Premium  | 1P 160                         |
| PS5              | Mortal Kombat 1      | Normal   | 1P 120; 2P 150                 |
| PS5              | Call of Duty: MW III | Premium  | 1P 140; 2P 180                 |
| PS5              | Astro's Playroom     | Normal   | 1P 100                         |
| PS4              | FIFA 23              | Normal   | 1P 100; 2P 130; 3P 150; 4P 170 |
| PS4              | God of War           | Premium  | 1P 120                         |
| PS4              | Tekken 7             | Normal   | 1P 90; 2P 120                  |
| PS4              | Minecraft            | Normal   | 1P 80; 2P 110; 3P 130; 4P 150  |
| PS3              | GTA V                | Premium  | 1P 80                          |
| PS3              | Call of Duty: BO2    | Normal   | 1P 60; 2P 80; 3P 100; 4P 120   |
| PS3              | Blur                 | Normal   | 1P 60; 2P 80; 3P 100; 4P 120   |
| RACING SIMULATOR | Gran Turismo 7       | Premium  | 1P 200                         |
| RACING SIMULATOR | F1 23                | Premium  | 1P 220                         |
| RACING SIMULATOR | Dirt Rally 2.0       | Normal   | 1P 150                         |
| ARCADE           | Street Fighter II    | Normal   | 1P 50; 2P 80                   |
| ARCADE           | Pac-Man              | Normal   | 1P 40; 2P 60                   |
| ARCADE           | Metal Slug           | Premium  | 1P 60; 2P 90                   |

# 9\. Functional Requirements

| **ID** | **Requirement**                         | **Acceptance Summary**                                                                                                        |
| ------ | --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| FR1    | Validate customer and booking inputs    | Reject invalid name, booking type, station, game, duration, player count, time, snack quantity, and skip-time inputs.         |
| FR2    | Select game by station                  | Only games belonging to the selected station type are displayed.                                                              |
| FR3    | Check availability                      | Inspect current occupancy and advance bookings for overlapping windows before allocation.                                     |
| FR4    | Support capacity and multi-unit booking | Calculate units_needed using the selected game's max_players and allocate multiple units when required.                       |
| FR5    | Support walk-in queue                   | If units are unavailable, offer queue placement; queues are FIFO by station type.                                             |
| FR6    | Support advance booking                 | Reserve specific available units for a future start time and activate them when the virtual clock reaches the scheduled time. |
| FR7    | Calculate gaming charge                 | Use the selected game's player-count pricing tier and bill actual duration, rounded up to the nearest rupee.                  |
| FR8    | Manage snacks and drinks                | Add menu items mid-session and at checkout and include them in the final bill.                                                |
| FR9    | Apply loyalty discount                  | Track cumulative hours by normalized customer name and apply 10% discount at >=10 hours.                                      |
| FR10   | Handle virtual time                     | Advance time, auto-close expired sessions, and activate due advance bookings.                                                 |
| FR11   | Bill expired sessions                   | Store auto-closed sessions and allow individual or grouped checkout before end of day.                                        |
| FR12   | Support group checkout                  | Use shared group_id for multi-unit sessions and produce one bill for grouped checkout.                                        |
| FR13   | End-of-day reset                        | At 22:00, clear operational state and reset the virtual clock to 10:00 while preserving loyalty hours.                        |

# 10\. Core Business Rules

- Operating hours are 10:00 through 22:00.
- Advance booking start time must not be in the past and the complete session must not run beyond closing.
- A game's max_players value determines the number of players a unit can serve for that game.
- Required units = ceil(total_players / game max_players).
- If enough units are available, the operator can book all required units, queue, or cancel.
- If only some units are available, the operator can proceed with the available capacity, queue, or cancel.
- Players are split as evenly as possible across the allocated units.
- All units in one multi-unit booking share a UUID group_id.
- Gaming charge = selected hourly tier × actual duration in hours, rounded upward with math.ceil.
- There is no separate AAA game surcharge in the current implementation; the selected game's pricing tier is the source of gaming cost.
- Food total is the sum of menu price × quantity.
- Subtotal = gaming charge + food total.
- A 10% loyalty discount applies when prior cumulative hours are at least 10.0.
- For a multi-unit parallel session, loyalty hours added are the maximum unit duration, not the sum.
- A minimum billed duration of one minute is used for manual checkout.

# 11\. Snack and Drink Menu

| **Item**   | **Price (Rs)** |
| ---------- | -------------- |
| Cold Drink | 40             |
| Chips      | 30             |
| Coffee     | 50             |
| Sandwich   | 80             |

# 12\. Booking and Session Flow

1. Operator chooses New Customer.
2. System validates customer name, booking type, station, game, duration, and player count.
3. For advance booking, the operator enters a future HH:MM start time.
4. System checks the selected game's maximum players and calculates required units.
5. System finds units that are free for the entire requested time window and not reserved by overlapping advance bookings.
6. The operator either receives an allocation or is offered queue/cancel alternatives.
7. For multi-unit bookings, players are distributed across units and a common group_id is generated.
8. The active session can receive snack orders while playing.
9. The operator ends the session manually or advances virtual time until the session expires.
10. The system calculates gaming cost, food cost, loyalty discount, and final total.
11. Loyalty hours are updated after billing.

# 13\. Billing Requirements

- Receipt includes customer, station type, duration, gaming charge, snacks, food total, subtotal, loyalty discount when applicable, and total due.
- For grouped sessions, gaming charges from all units are combined.
- For grouped sessions with different station types, the receipt station label becomes 'Multiple Units'.
- Expired sessions use stored actual_dur_min rather than the current virtual time.
- Mid-session snacks and checkout snacks are merged.

# 14\. Virtual Clock and End-of-Day

- Virtual clock starts at 10:00 and is stored as minutes since midnight.
- Skipping time does not exceed 22:00; the requested advance is capped at closing.
- Sessions ending at or before the new clock time are moved to expired_sessions.
- Due advance bookings are activated after time advancement.
- At 22:00, the application offers a new-day reset or quit.
- Stations, queues, advance bookings, and expired sessions are cleared on reset.
- loyalty_hours persists across days.

# 15\. Non-Functional Requirements

| **Area**        | **Requirement**                                                                                |
| --------------- | ---------------------------------------------------------------------------------------------- |
| Usability       | Numbered menus and clear validation messages suitable for a terminal operator.                 |
| Correctness     | Pricing, availability, duration, queue, group, and loyalty calculations must be deterministic. |
| Maintainability | Responsibilities are separated across data.py, inputs.py, logic.py, and main.py.               |
| Performance     | In-memory dictionaries/lists provide responsive operation for the small café dataset.          |
| Portability     | Runs as a Python console application without a database or external service.                   |
| Reliability     | Invalid inputs are re-prompted instead of terminating the application.                         |

# 16\. Current File Structure

| **File**  | **Primary Responsibility**                                                                          |
| --------- | --------------------------------------------------------------------------------------------------- |
| main.py   | Application entry point, menus, booking/session orchestration, checkout, expired-session billing.   |
| inputs.py | User-facing input collection and validation.                                                        |
| logic.py  | Availability, booking priority, queues, virtual time, billing, loyalty, station state transitions.  |
| data.py   | Static catalog, prices, stations, queues, bookings, expired sessions, loyalty hours, virtual clock. |

# 17\. Acceptance / Test Matrix

| **ID** | **Scenario**              | **Input/Condition**                              | **Expected Result**                    |
| ------ | ------------------------- | ------------------------------------------------ | -------------------------------------- |
| TC01   | Valid walk-in             | Valid customer, station, game, duration, players | Unit allocated and start/end displayed |
| TC02   | Invalid name              | Empty or symbol-only                             | Re-prompt                              |
| TC03   | Invalid duration          | 0, negative, malformed, >12                      | Re-prompt                              |
| TC04   | Invalid players           | 0, negative, decimal/text                        | Re-prompt                              |
| TC05   | Game filtering            | Choose PS5                                       | Only PS5 games shown                   |
| TC06   | Dynamic pricing           | EA FC 24 with 1P/2P/3P/4P                        | Correct hourly tier selected           |
| TC07   | Capacity exceeded         | More players than game max_players               | Multiple-unit/queue/cancel flow        |
| TC08   | No availability           | All matching units occupied                      | Queue or cancel                        |
| TC09   | Advance booking           | Future HH:MM                                     | Specific unit reserved                 |
| TC10   | Double-booking prevention | Overlapping reservation                          | Unit excluded                          |
| TC11   | Mid-session snacks        | Add drink/chips                                  | Items stored in booking                |
| TC12   | Manual checkout           | End active session                               | Itemized bill printed                  |
| TC13   | Auto-close                | Skip beyond session end                          | Session moved to expired list          |
| TC14   | Expired billing           | Select expired session                           | Bill uses stored actual duration       |
| TC15   | Loyalty                   | Cumulative hours >=10                            | 10% discount                           |
| TC16   | Group checkout            | Two units share group_id                         | One combined bill                      |
| TC17   | End of day                | Clock reaches 22:00                              | Reset or quit prompt                   |
| TC18   | New-day persistence       | After reset                                      | Loyalty hours remain                   |

# 18\. Limitations and Future Enhancements

- Operational data is in memory and is lost when the program exits.
- There is no database or persistent transaction history.
- The interface is terminal-only.
- There is no authentication or role management.
- There is no integrated payment gateway.
- There is no reporting dashboard.
- Future versions could add persistence, GUI/web UI, customer profiles, payment methods, analytics, and automated notifications.

# 19\. Traceability to Current Repository

This PRD was prepared from the current public repository structure and source files. The repository currently contains data.py, inputs.py, logic.py, and main.py on the main branch. The current implementation defines game-specific pricing by player count, game max_players, physical station units, queues, advance bookings, expired sessions, and loyalty state.

Reference documents supplied with this task were treated as formatting/content-organization references. Where they differed from the current repository implementation, the current repository was used as the source of truth.