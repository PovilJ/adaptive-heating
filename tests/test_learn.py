"""The house learning itself: the half-hour log, the daily refit and its gate, the heat pump's own values."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import math
import unittest

from common import module

mpc = module("mpc")
learn = module("learn")
PLACE = (54.6, 25.1)
START = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc).timestamp()


def recorded(house, days, cloud=40, seed=7):
    """Rows a coordinator would log from `house` heated by on/off runs, outdoors swinging 2–12 °C."""
    rows, state, t = [], house.resting(22.0, 7.0), START
    rnd = seed
    for i in range(days * 48):
        when = datetime.fromtimestamp(t, timezone.utc)
        outdoor = 7 + 5 * math.sin(2 * math.pi * ((i / 48) - 0.375))
        room = house.room(state)
        rnd = (rnd * 1103515245 + 12345) % 2 ** 31
        heat = 6.0 if room < 22.0 else 0.0
        sun = mpc.sunshine(when + timedelta(minutes=15), *PLACE, cloud)
        rows.append(learn.Row(t, round(room * 5) / 5 if rnd % 3 else room, outdoor, heat, 0.5, cloud, None,
                              31.0 if heat else 25.0, state[0], state[0] + (5 if heat else 2.7), 1.0 if heat else 0.0))
        state = house.step(state, heat, outdoor, sun)
        t += 1800
    return rows


class Log(unittest.TestCase):
    def add(self, log, minutes, energy, **kw):
        values = dict(room=22.0, outdoor=5.0, cloud=50.0, pv_ratio=None, setpoint=30.0, slab=24.0, outlet=27.0,
                      duty=1.0, floor_heat=True, cop_water=30.0, house=mpc.House()) | kw
        return log.add(now=START + minutes * 60, energy_kwh=energy, **values)

    def test_a_row_per_interval_with_heat_from_the_meter(self):
        log = learn.Log()
        self.assertFalse(self.add(log, 0, 100.0))
        self.assertFalse(self.add(log, 2, 100.03))   # a paused two-minute cycle closes nothing
        self.assertTrue(self.add(log, 30, 100.6))
        row = log.rows[0]
        cop = mpc.House().cop(30.0, 5.0)
        self.assertAlmostEqual(row.heat, (1.2 - learn.STANDBY_KW) * cop, places=3)
        self.assertAlmostEqual(row.duty, 1.0)

    def test_hot_water_or_ac_makes_the_interval_unknown_but_keeps_the_room(self):
        log = learn.Log()
        self.add(log, 0, 100.0)
        self.add(log, 10, 100.5, floor_heat=False)
        self.add(log, 30, 101.5)
        self.assertIsNone(log.rows[0].heat)
        self.assertEqual(log.rows[0].room, 22.0)

    def test_a_silence_breaks_the_record_and_old_rows_expire(self):
        log = learn.Log()
        self.add(log, 0, 100.0)
        self.add(log, 120, 101.0)  # two hours of nothing: no row spans it
        self.assertEqual(log.rows, [])
        for i in range(1, 30 * 48):
            self.add(log, 120 + 30 * i, 101.0 + i * 0.1)
        self.assertLessEqual(log.rows[-1].t - log.rows[0].t, learn.KEEP_DAYS * 86400)

    def test_it_survives_storage(self):
        log = learn.Log()
        for i in range(5):
            self.add(log, 30 * i, 100 + i * 0.4)
        again = learn.Log.restore(log.to_dict())
        self.assertEqual([r.to_list() for r in again.rows], [r.to_list() for r in log.rows])
        self.assertEqual(learn.Log.restore({"rows": [["bad"]]}).rows, [])


class Refit(unittest.TestCase):
    def test_a_leakier_house_is_found_and_adopted(self):
        start = mpc.House()
        truth = replace(start, loss=start.loss * 1.4)  # October here: 0.19 kW/°C against the winter 0.14
        rows = recorded(truth, 10)
        house, report = learn.refit(start, rows, PLACE, rows[-1].t + 1800)
        self.assertTrue(report.adopted, report.reason)
        self.assertLess(report.error_after, report.error_before)
        ua = lambda h: learn.physical_of(h)[0]
        self.assertLess(abs(ua(house) - ua(truth)), 0.35 * abs(ua(start) - ua(truth)))
        # What the data cannot tell apart stays where it was.
        self.assertAlmostEqual(house.heat, start.heat, places=6)
        self.assertAlmostEqual(house.release, start.release, places=6)

    def test_the_right_house_stays_put(self):
        rows = recorded(mpc.House(), 10)
        house, report = learn.refit(mpc.House(), rows, PLACE, rows[-1].t + 1800)
        found, true = learn.physical_of(house), learn.physical_of(mpc.House())
        self.assertLess(abs(found[0] - true[0]), 0.05 * true[0])  # heat loss
        for i in (4, 5, 6):  # sun on the east, south and west walls, in °C/h per kW/m²
            self.assertLess(abs(found[i] - true[i]), 0.4)
        for i in set(range(len(true))) - set(learn.FREE):
            self.assertEqual(found[i], true[i])

    def test_it_waits_for_three_days(self):
        rows = recorded(mpc.House(), 2)
        house, report = learn.refit(mpc.House(), rows, PLACE, rows[-1].t + 1800)
        self.assertFalse(report.adopted)
        self.assertIn("Waiting for data", report.reason)

    def test_stored_values_round_trip_and_bad_ones_fall_back(self):
        house = replace(mpc.House(), loss=0.009, restart_gap=4.5)
        self.assertEqual(learn.house_from_dict(learn.house_to_dict(house), mpc.House()), house)
        self.assertEqual(learn.house_from_dict({"loss": "x"}, mpc.House()), mpc.House())
        self.assertEqual(learn.house_from_dict({"loss": float("nan")}, mpc.House()).loss, mpc.House().loss)


class Device(unittest.TestCase):
    def test_restart_gap_comes_from_the_smallest_gaps_that_started(self):
        self.assertEqual(learn.restart_gap([5.2, 6.5], 5.0), 5.0)  # too few
        # 11-18 Oct 2026, the first house
        gaps = [5.2, 6.5, 4.6, 5.7, 6.0, 4.8, 5.9, 4.7, 4.6, 7.1, 4.5, 4.5, 6.2, 5.4, 6.0, 5.1, 4.6]
        self.assertEqual(learn.restart_gap(gaps, 5.0), 4.5)

    def test_minimum_output_and_resting_outlet_are_measured(self):
        rows = recorded(mpc.House(), 6)
        found = learn.fit_device(rows, mpc.House())
        self.assertAlmostEqual(found["idle_offset"], 2.7, places=6)
        self.assertAlmostEqual(found["q_min"], 6.0, places=6)

    def test_pv_measures_the_sky(self):
        rows = [learn.Row(START + i, 22, 5, 0, 0.5, 50, 8000.0 * (i % 10) / 9, None, None, None, None) for i in range(100)]
        scale = learn.pv_scale(rows)
        self.assertAlmostEqual(scale, 8000.0, places=3)
        self.assertAlmostEqual(learn.clearness(4000.0, scale), 0.5)
        self.assertIsNone(learn.clearness(None, scale))
        self.assertIsNone(learn.pv_scale(rows[:10]))


if __name__ == "__main__":
    unittest.main()
