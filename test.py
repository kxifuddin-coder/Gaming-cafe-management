import unittest
import data
import logic

class GamingCafeTests(unittest.TestCase):

    def setUp(self):
        # Reset the mock state before each test
        logic.start_new_day()
        data.loyalty_hours.clear()
        for q in data.queues.values():
            q.clear()
        data.advance_bookings.clear()
        data.expired_sessions.clear()
        
    def test_dynamic_pricing_calculation(self):
        """Test dynamic pricing based on game type and exact/over-cap player count."""
        charge1 = logic.calculate_gaming_charge("PS5", "EA FC 24", 2, 120)  # 180/hr * 2 = 360
        self.assertEqual(charge1, 360)
        
        charge2 = logic.calculate_gaming_charge("PS5", "EA FC 24", 5, 60)   # Max tier is 4 (220/hr)
        self.assertEqual(charge2, 220)
        
        charge3 = logic.calculate_gaming_charge("PS5", "Spider-Man 2", 1, 30) # 160/hr * 0.5 = 80
        self.assertEqual(charge3, 80)

    def test_loyalty_discount_exact_boundaries(self):
        """Test loyalty discount at strict float boundaries."""
        # Under threshold (9.99 hours)
        data.loyalty_hours["ALICE"] = 9.99
        self.assertEqual(logic.apply_loyalty_discount("Alice", 1000), 1000)
        
        # Exactly threshold (10.0 hours)
        data.loyalty_hours["BOB"] = 10.0
        self.assertEqual(logic.apply_loyalty_discount("Bob", 1000), 900)

        # Over threshold (10.01 hours)
        data.loyalty_hours["CHARLIE"] = 10.01
        self.assertEqual(logic.apply_loyalty_discount("Charlie", 1000), 900)

    def test_allocate_and_release_station(self):
        """Test proper tracking of active sessions and state transitions."""
        booking = {
            "customer_name": "Alice",
            "station_type": "PS5",
            "game_name": "EA FC 24",
            "duration_hrs": 2,
            "player_count": 2,
            "scheduled_start": 600,
            "snacks": []
        }
        
        logic.allocate_station(5, booking)
        self.assertTrue(data.stations[5]["occupied"])
        self.assertEqual(data.stations[5]["current_booking"]["customer_name"], "Alice")
        self.assertEqual(data.stations[5]["session_end"], 720) 
        
        logic.release_station(5)
        self.assertFalse(data.stations[5]["occupied"])
        self.assertIsNone(data.stations[5]["current_booking"])

    def test_queue_isolation_multiple_types(self):
        """Test walk-ins are queued correctly strictly isolated by station type."""
        logic.add_to_queue("Alice", "PS5")
        logic.add_to_queue("Bob", "PS5")
        logic.add_to_queue("Charlie", "PS4")
        
        self.assertEqual(data.queues["PS5"], ["Alice", "Bob"])
        self.assertEqual(data.queues["PS4"], ["Charlie"])
        self.assertEqual(len(data.queues["ARCADE"]), 0)

    def test_availability_overlap_detection(self):
        """Test robust time-overlap detection for future advance bookings."""
        # Setup: Advance booking on unit 5 from 14:00 (840) to 16:00 (960)
        bk = {
            "customer_name": "Dave",
            "station_type": "PS5",
            "game_name": "EA FC 24",
            "duration_hrs": 2,
            "player_count": 2,
            "scheduled_start": 840,
            "unit_id": 5,
            "snacks": []
        }
        data.advance_bookings.append(bk)
        
        # Test 1: Booking from 12:00 (720) to 14:00 (840) -> NO OVERLAP (ends exactly when Dave starts)
        available = logic.get_available_units("PS5", 720, 120)
        self.assertIn(5, available)

        # Test 2: Booking from 13:00 (780) to 15:00 (900) -> OVERLAPS
        available_overlap = logic.get_available_units("PS5", 780, 120)
        self.assertNotIn(5, available_overlap)

        # Test 3: Booking from 16:00 (960) to 18:00 (1080) -> NO OVERLAP
        available_after = logic.get_available_units("PS5", 960, 120)
        self.assertIn(5, available_after)

    def test_auto_close_sessions_on_time_skip(self):
        """Test that sessions strictly expire when the virtual clock hits their exact end_time."""
        booking = {
            "customer_name": "Eve",
            "station_type": "PS5",
            "game_name": "EA FC 24",
            "duration_hrs": 2,
            "player_count": 2,
            "scheduled_start": data.OPEN_HOUR * 60,
            "snacks": []
        }
        logic.allocate_station(5, booking) # Ends at OPEN_HOUR + 2 hrs
        
        # Skip to 1 minute before end
        logic.skip_time(119)
        self.assertTrue(data.stations[5]["occupied"])
        self.assertEqual(len(data.expired_sessions), 0)

        # Skip the final minute
        logic.skip_time(1)
        self.assertFalse(data.stations[5]["occupied"])
        self.assertEqual(len(data.expired_sessions), 1)
        self.assertEqual(data.expired_sessions[0]["customer_name"], "Eve")

    def test_time_parsing_and_formatting(self):
        """Test utility time manipulation functions and ValueError bounds."""
        self.assertEqual(data.fmt_time(0), "00:00")
        self.assertEqual(data.fmt_time(1439), "23:59")
        self.assertEqual(data.parse_time("14:30"), 870)
        
        with self.assertRaises(ValueError):
            data.parse_time("25:00") # Invalid hour
        with self.assertRaises(ValueError):
            data.parse_time("12:60") # Invalid minute
        with self.assertRaises(ValueError):
            data.parse_time("abc")   # Invalid string

    def test_food_total_calculation(self):
        """Test sum of snacks is computed properly."""
        items = [("COLD DRINK", 2), ("SANDWICH", 1)]
        # COLD DRINK = 40, SANDWICH = 80 => 2*40 + 80 = 160
        total = logic.calculate_food_total(items)
        self.assertEqual(total, 160)

    def test_start_new_day(self):
        """Test end-of-day flow wipes temporary data, resets clock, but preserves loyalty."""
        data.loyalty_hours["BOB"] = 15
        data.queues["PS5"].append("Alice")
        data.expired_sessions.append({"unit_id": 5})
        data.set_time(1200) # 20:00
        
        logic.start_new_day()
        
        self.assertEqual(len(data.queues["PS5"]), 0)
        self.assertEqual(len(data.expired_sessions), 0)
        self.assertEqual(data.loyalty_hours["BOB"], 15)
        self.assertEqual(data.get_time(), data.OPEN_HOUR * 60)

if __name__ == '__main__':
    unittest.main()
