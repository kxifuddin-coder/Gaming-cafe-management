"""Unit tests for the Gaming Café project.

Run from the project folder with:
    python -m unittest -v test_complete.py

Tests cover data/state, business logic, input validation, and selected main flows.
"""
import unittest
from unittest.mock import patch

import data
import inputs
import logic
import main


class GamingCafeTests(unittest.TestCase):
    def setUp(self):
        logic.start_new_day()
        data.loyalty_hours.clear()
        for queue in data.queues.values():
            queue.clear()
        data.advance_bookings.clear()
        data.expired_sessions.clear()

    # Existing test cases
    def test_dynamic_pricing_calculation(self):
        self.assertEqual(logic.calculate_gaming_charge("PS5", "EA FC 24", 2, 120), 360)
        self.assertEqual(logic.calculate_gaming_charge("PS5", "EA FC 24", 5, 60), 220)
        self.assertEqual(logic.calculate_gaming_charge("PS5", "Spider-Man 2", 1, 30), 80)

    def test_loyalty_discount_exact_boundaries(self):
        data.loyalty_hours["ALICE"] = 9.99
        self.assertEqual(logic.apply_loyalty_discount("Alice", 1000), 1000)
        data.loyalty_hours["BOB"] = 10.0
        self.assertEqual(logic.apply_loyalty_discount("Bob", 1000), 900)
        data.loyalty_hours["CHARLIE"] = 10.01
        self.assertEqual(logic.apply_loyalty_discount("Charlie", 1000), 900)

    def test_allocate_and_release_station(self):
        booking = {"customer_name": "Alice", "station_type": "PS5", "game_name": "EA FC 24",
                   "duration_hrs": 2, "player_count": 2, "scheduled_start": 600, "snacks": []}
        logic.allocate_station(5, booking)
        self.assertTrue(data.stations[5]["occupied"])
        self.assertEqual(data.stations[5]["current_booking"]["customer_name"], "Alice")
        self.assertEqual(data.stations[5]["session_end"], 720)
        logic.release_station(5)
        self.assertFalse(data.stations[5]["occupied"])
        self.assertIsNone(data.stations[5]["current_booking"])
        self.assertIsNone(data.stations[5]["session_start"])
        self.assertIsNone(data.stations[5]["session_end"])

    def test_queue_isolation_multiple_types(self):
        logic.add_to_queue("Alice", "PS5")
        logic.add_to_queue("Bob", "PS5")
        logic.add_to_queue("Charlie", "PS4")
        self.assertEqual(data.queues["PS5"], ["Alice", "Bob"])
        self.assertEqual(data.queues["PS4"], ["Charlie"])
        self.assertEqual(data.queues["ARCADE"], [])

    def test_availability_overlap_detection(self):
        booking = {"customer_name": "Dave", "station_type": "PS5", "game_name": "EA FC 24",
                   "duration_hrs": 2, "player_count": 2, "scheduled_start": 840,
                   "unit_id": 5, "snacks": []}
        data.advance_bookings.append(booking)
        self.assertIn(5, logic.get_available_units("PS5", 720, 120))
        self.assertNotIn(5, logic.get_available_units("PS5", 780, 120))
        self.assertIn(5, logic.get_available_units("PS5", 960, 120))

    def test_auto_close_sessions_on_time_skip(self):
        booking = {"customer_name": "Eve", "station_type": "PS5", "game_name": "EA FC 24",
                   "duration_hrs": 2, "player_count": 2, "scheduled_start": data.OPEN_HOUR * 60,
                   "snacks": []}
        logic.allocate_station(5, booking)
        logic.skip_time(119)
        self.assertTrue(data.stations[5]["occupied"])
        self.assertEqual(len(data.expired_sessions), 0)
        logic.skip_time(1)
        self.assertFalse(data.stations[5]["occupied"])
        self.assertEqual(len(data.expired_sessions), 1)
        self.assertEqual(data.expired_sessions[0]["customer_name"], "Eve")

    def test_time_parsing_and_formatting(self):
        self.assertEqual(data.fmt_time(0), "00:00")
        self.assertEqual(data.fmt_time(1439), "23:59")
        self.assertEqual(data.parse_time("14:30"), 870)
        for invalid in ("25:00", "12:60", "abc"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                data.parse_time(invalid)

    def test_food_total_calculation(self):
        self.assertEqual(logic.calculate_food_total([("COLD DRINK", 2), ("SANDWICH", 1)]), 160)

    def test_start_new_day(self):
        data.loyalty_hours["BOB"] = 15
        data.queues["PS5"].append("Alice")
        data.expired_sessions.append({"unit_id": 5})
        data.set_time(1200)
        logic.start_new_day()
        self.assertEqual(data.queues["PS5"], [])
        self.assertEqual(data.expired_sessions, [])
        self.assertEqual(data.loyalty_hours["BOB"], 15)
        self.assertEqual(data.get_time(), data.OPEN_HOUR * 60)

    # data.py and clock edge cases
    def test_initial_virtual_time_is_opening_time(self):
        self.assertEqual(data.get_time(), data.OPEN_HOUR * 60)

    def test_set_and_advance_time(self):
        data.set_time(720)
        self.assertEqual(data.get_time(), 720)
        data.advance_time(45)
        self.assertEqual(data.get_time(), 765)

    def test_parse_time_with_surrounding_whitespace(self):
        self.assertEqual(data.parse_time(" 14:30 "), 870)

    def test_parse_time_rejects_bad_formats_and_ranges(self):
        for invalid in ("", "14", "14:30:00", "-1:00", "24:00", "12:99", "x:30"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                data.parse_time(invalid)

    # logic.py and business-rule edge cases
    def test_cafe_opening_boundary(self):
        self.assertFalse(logic.is_cafe_open(data.OPEN_HOUR * 60 - 1))
        self.assertTrue(logic.is_cafe_open(data.OPEN_HOUR * 60))

    def test_cafe_closing_boundary(self):
        self.assertTrue(logic.is_cafe_open(data.CLOSE_HOUR * 60 - 1))
        self.assertFalse(logic.is_cafe_open(data.CLOSE_HOUR * 60))

    def test_availability_allows_sessions_touching_at_boundary(self):
        booking = {"customer_name": "Booked", "station_type": "PS5", "game_name": "EA FC 24",
                   "duration_hrs": 1, "player_count": 2, "scheduled_start": 840,
                   "unit_id": 5, "snacks": []}
        data.advance_bookings.append(booking)
        self.assertIn(5, logic.get_available_units("PS5", 780, 60))
        self.assertIn(5, logic.get_available_units("PS5", 900, 60))

    def test_occupied_unit_without_session_times_is_unavailable(self):
        data.stations[5]["occupied"] = True
        data.stations[5]["session_start"] = None
        data.stations[5]["session_end"] = None
        self.assertNotIn(5, logic.get_available_units("PS5", 720, 60))

    def test_advance_bookings_are_sorted(self):
        late = {"customer_name": "Late", "scheduled_start": 900}
        early = {"customer_name": "Early", "scheduled_start": 720}
        logic.register_advance_booking(late)
        logic.register_advance_booking(early)
        self.assertEqual([b["customer_name"] for b in data.advance_bookings], ["Early", "Late"])

    def test_upcoming_booking_within_30_minutes(self):
        data.set_time(600)
        booking = {"customer_name": "Reserved", "station_type": "PS5", "scheduled_start": 625,
                   "duration_hrs": 1, "unit_id": 5}
        logic.register_advance_booking(booking)
        self.assertEqual(logic._upcoming_booking(5), booking)

    def test_upcoming_booking_outside_30_minutes_returns_none(self):
        data.set_time(600)
        booking = {"customer_name": "Later", "station_type": "PS5", "scheduled_start": 631,
                   "duration_hrs": 1, "unit_id": 5}
        logic.register_advance_booking(booking)
        self.assertIsNone(logic._upcoming_booking(5))

    def test_due_advance_booking_activates_after_time_skip(self):
        booking = {"customer_name": "Booked", "station_type": "PS5", "game_name": "EA FC 24",
                   "duration_hrs": 1, "player_count": 2, "scheduled_start": 660,
                   "unit_id": 5, "snacks": []}
        logic.register_advance_booking(booking)
        logic.skip_time(60)
        self.assertTrue(data.stations[5]["occupied"])
        self.assertEqual(data.stations[5]["current_booking"]["customer_name"], "Booked")
        self.assertNotIn(booking, data.advance_bookings)

    def test_due_booking_stays_pending_if_assigned_station_is_occupied(self):
        active = {"customer_name": "Current", "station_type": "PS5", "game_name": "EA FC 24",
                  "duration_hrs": 2, "player_count": 2, "scheduled_start": 600, "snacks": []}
        logic.allocate_station(5, active)
        waiting = {"customer_name": "Next", "station_type": "PS5", "game_name": "EA FC 24",
                   "duration_hrs": 1, "player_count": 2, "scheduled_start": 610,
                   "unit_id": 5, "snacks": []}
        logic.register_advance_booking(waiting)
        logic.skip_time(15)
        self.assertTrue(data.stations[5]["occupied"])
        self.assertIn(waiting, data.advance_bookings)

    def test_empty_food_order_total_is_zero(self):
        self.assertEqual(logic.calculate_food_total([]), 0)

    def test_fractional_hour_gaming_charge_rounds_up(self):
        self.assertEqual(logic.calculate_gaming_charge("PS5", "EA FC 24", 2, 1), 3)

    def test_unknown_customer_receives_no_loyalty_discount(self):
        self.assertEqual(logic.apply_loyalty_discount("Unknown", 1000), 1000)

    def test_add_loyalty_hours_is_case_insensitive(self):
        logic.add_loyalty_hours("Kaif", 2)
        logic.add_loyalty_hours("KAIF", 3)
        self.assertEqual(data.loyalty_hours["KAIF"], 5)

    def test_start_new_day_clears_active_stations(self):
        booking = {"customer_name": "Active", "station_type": "PS5", "game_name": "EA FC 24",
                   "duration_hrs": 1, "player_count": 2, "scheduled_start": 600, "snacks": []}
        logic.allocate_station(5, booking)
        logic.start_new_day()
        self.assertFalse(data.stations[5]["occupied"])
        self.assertIsNone(data.stations[5]["current_booking"])
        self.assertIsNone(data.stations[5]["session_start"])
        self.assertIsNone(data.stations[5]["session_end"])

    # inputs.py validation tests
    def test_customer_name_retries_after_empty_input(self):
        with patch("builtins.input", side_effect=["", "Kaif"]):
            self.assertEqual(inputs.get_customer_name(), "Kaif")

    def test_customer_name_rejects_digits_and_symbols_only(self):
        with patch("builtins.input", side_effect=["12345", "@@@", "Kaif"]):
            self.assertEqual(inputs.get_customer_name(), "Kaif")

    def test_customer_name_strips_surrounding_whitespace(self):
        with patch("builtins.input", return_value="  Alice  "):
            self.assertEqual(inputs.get_customer_name(), "Alice")

    def test_booking_type_retries_after_invalid_choice(self):
        with patch("builtins.input", side_effect=["3", "2"]):
            self.assertEqual(inputs.get_booking_type(), "W")

    def test_station_type_retries_after_out_of_range_choice(self):
        ps5_choice = str(list(data.GAMES_CATALOG.keys()).index("PS5") + 1)
        with patch("builtins.input", side_effect=["99", ps5_choice]):
            self.assertEqual(inputs.get_station_type(data.GAMES_CATALOG), "PS5")

    def test_game_choice_retries_after_invalid_choice(self):
        with patch("builtins.input", side_effect=["0", "1"]):
            self.assertEqual(inputs.get_game_choice("PS5", data.GAMES_CATALOG), "EA FC 24")

    def test_duration_rejects_zero_and_over_12_hours(self):
        with patch("builtins.input", side_effect=["0", "13", "1.5"]):
            self.assertEqual(inputs.get_duration(), 1.5)

    def test_duration_rejects_text_and_malformed_decimal(self):
        with patch("builtins.input", side_effect=["abc", "1.5.0", "2"]):
            self.assertEqual(inputs.get_duration(), 2.0)

    def test_player_count_rejects_decimal_and_zero(self):
        with patch("builtins.input", side_effect=["2.5", "0", "3"]):
            self.assertEqual(inputs.get_player_count(), 3)

    def test_snack_order_accepts_empty_order(self):
        with patch("builtins.input", return_value=""):
            self.assertEqual(inputs.get_snack_order(data.MENU, data.MENU_LABELS), [])

    def test_snack_order_retries_invalid_quantity(self):
        number = next(n for n, key in data.MENU_LABELS.items() if key == "COLD DRINK")
        with patch("builtins.input", side_effect=[str(number), "0", str(number), "1", "0"]):
            self.assertEqual(inputs.get_snack_order(data.MENU, data.MENU_LABELS), [("COLD DRINK", 1)])

    def test_scheduled_start_rejects_invalid_time_then_accepts_valid_time(self):
        with patch("builtins.input", side_effect=["25:00", "09:00", "14:30"]):
            self.assertEqual(inputs.get_scheduled_start(600, 1320, 600), 870)

    def test_scheduled_start_rejects_time_in_the_past(self):
        with patch("builtins.input", side_effect=["10:30", "11:00"]):
            self.assertEqual(inputs.get_scheduled_start(600, 1320, 660), 660)

    def test_skip_minutes_rejects_invalid_values(self):
        for invalid in ("abc", "0", "-5", "721", "2.5"):
            with self.subTest(value=invalid), patch("builtins.input", return_value=invalid):
                self.assertEqual(inputs.get_skip_minutes(), 0)

    # main.py flow / defensive tests
    def test_new_customer_when_cafe_is_closed_does_not_prompt(self):
        data.set_time(data.CLOSE_HOUR * 60)
        with patch("builtins.input") as mocked_input:
            main.run_new_customer()
        mocked_input.assert_not_called()

    def test_select_occupied_unit_when_none_active(self):
        with patch("builtins.input") as mocked_input:
            self.assertIsNone(main._select_occupied_unit())
        mocked_input.assert_not_called()

    def test_remove_from_empty_queue_does_not_prompt(self):
        with patch("builtins.input") as mocked_input:
            main.remove_from_queue()
        mocked_input.assert_not_called()

    def test_cancel_when_no_advance_bookings_does_not_prompt(self):
        with patch("builtins.input") as mocked_input:
            main.cancel_advance_booking()
        mocked_input.assert_not_called()

    def test_remove_from_queue_removes_selected_customer(self):
        data.queues["PS5"].extend(["Alice", "Bob"])
        with patch("builtins.input", side_effect=["1", "2"]):
            main.remove_from_queue()
        self.assertEqual(data.queues["PS5"], ["Alice"])

    def test_cancel_advance_booking_removes_selected_booking(self):
        booking = {"customer_name": "Alice", "station_type": "PS5", "scheduled_start": 720,
                   "duration_hrs": 1, "unit_id": 5}
        data.advance_bookings.append(booking)
        with patch("builtins.input", return_value="1"):
            main.cancel_advance_booking()
        self.assertEqual(data.advance_bookings, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

