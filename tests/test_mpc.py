"""The predictive planner: the house model, the plan search and their safety nets."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest

from common import module

mpc = module("mpc")
PLACE = (54.7, 25.3)
MIDNIGHT = datetime(2026, 10, 10, 21, 0, tzinfo=timezone.utc)  # local midnight at UTC+3


def steps(start, outdoor, cloud, comfort):
    rows = [(start + timedelta(hours=h), outdoor, cloud) for h in range(40)]
    return mpc.horizon(start, rows, comfort, *PLACE, outdoor, 3.0)


class HouseModel(unittest.TestCase):
    def test_sun_is_in_the_east_in_the_morning_and_gone_at_night(self):
        morning = mpc.sunshine(datetime(2026, 10, 10, 6, 0, tzinfo=timezone.utc), *PLACE, 0)
        self.assertGreater(morning[0], morning[2])
        self.assertEqual(mpc.sunshine(MIDNIGHT, *PLACE, 0), (0.0, 0.0, 0.0, 0.0))
        overcast = mpc.sunshine(datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc), *PLACE, 100)
        clear = mpc.sunshine(datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc), *PLACE, 0)
        self.assertLess(overcast[1], clear[1] / 3)

    def test_unheated_house_cools_and_heat_warms_it(self):
        house = mpc.House()
        state = cold = house.resting(22.5, 5)
        for _ in range(12):
            cold = house.step(cold, 0.0, 5, (0, 0, 0, 0))
            state = house.step(state, 6.0, 5, (0, 0, 0, 0))
        self.assertLess(house.room(cold), 22.5)
        self.assertGreater(house.room(state), 22.5)

    def test_water_near_the_slab_delivers_nothing(self):
        house = mpc.House()
        self.assertEqual(house.heat_kw(25, 24), 0)
        self.assertGreater(house.heat_kw(31, 24), 3)


class Planning(unittest.TestCase):
    def setUp(self):
        self.house, self.comfort = mpc.House(), mpc.Comfort(target=22.5)

    def plan(self, start, outdoor, cloud, room=22.5, comfort=None):
        comfort = comfort or self.comfort
        return mpc.plan(self.house, comfort, steps(start, outdoor, cloud, comfort), self.house.resting(room, outdoor))

    def test_room_above_target_gets_minimum_water(self):
        self.assertEqual(self.plan(MIDNIGHT, 8, 90, room=23.5).water, self.comfort.minimum_water)

    def test_cold_room_in_cold_weather_gets_hot_water(self):
        self.assertGreater(self.plan(MIDNIGHT + timedelta(hours=12), -10, 90, room=21.5).water, 32)

    def test_plan_keeps_a_cold_day_inside_the_band(self):
        result = self.plan(MIDNIGHT, -5, 90)
        floors = [s.floor for s in steps(MIDNIGHT, -5, 90, self.comfort)]
        self.assertTrue(all(room > floor - 0.4 for room, floor in zip(result.rooms, floors)))

    def test_sunshine_saves_electricity_and_night_setback_never_costs_much(self):
        self.assertLess(self.plan(MIDNIGHT, 5, 0).energy_kwh, self.plan(MIDNIGHT, 5, 100).energy_kwh)
        # A heavy house regains a setback at hotter, less efficient water: allowed, not assumed to pay.
        flat = replace(self.comfort, night_floor=22.5)
        self.assertLess(self.plan(MIDNIGHT, 0, 90).energy_kwh, 1.05 * self.plan(MIDNIGHT, 0, 90, comfort=flat).energy_kwh)

    def test_guard_raises_water_while_the_room_stays_under_its_band(self):
        guard = mpc.Guard()
        self.assertEqual([guard.update(21.8, 22.5) for _ in range(3)], [1, 2, 3])
        self.assertEqual(guard.update(22.5, 22.5), 2)
        self.assertEqual(guard.update(22.4, 22.5), 2)  # inside the 0.2 °C sensor step: hold

    def test_estimate_blames_the_slab_at_night_and_the_sun_by_day(self):
        night, day = mpc.Estimate(), mpc.Estimate()
        noon = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)
        for estimate, when in ((night, MIDNIGHT), (day, noon)):
            sun = mpc.sunshine(when, *PLACE, 0)
            estimate.update(self.house, when.timestamp(), 22.5, 5, None, 0, sun)
            estimate.update(self.house, when.timestamp() + 1800, 23.0, 5, None, 0, sun)
        self.assertGreater(night.slab, day.slab)
        self.assertGreater(day.glow, night.glow)
        self.assertAlmostEqual(self.house.room(night.state(self.house)), 23.0, places=6)

    def test_startup_mismatch_does_not_become_a_large_permanent_drift(self):
        estimate, noon = mpc.Estimate(), datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)
        for cycle in range(6):  # a room that keeps reading cooler than the model expects, in daylight
            estimate.update(self.house, noon.timestamp() + 1800 * cycle, 23.7 - 0.05 * cycle, 9, None, 0,
                            mpc.sunshine(noon, *PLACE, 90))
        self.assertLessEqual(abs(estimate.bias), 0.05)
        self.assertAlmostEqual(estimate.predicted, 23.45, delta=0.3)


if __name__ == "__main__":
    unittest.main()
