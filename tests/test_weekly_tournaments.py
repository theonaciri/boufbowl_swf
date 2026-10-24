"""Paris wall-clock recurrence survives daylight saving and match overruns."""
from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from backend.service import Service
from backend.tournaments import occurrence_window
from tools.game_config import load_config

PARIS = ZoneInfo('Europe/Paris')


def stamp(year, month, day, hour):
    return int(datetime(year, month, day, hour, tzinfo=PARIS).timestamp())


class WeeklyTournamentTests(unittest.TestCase):
    def test_fall_back_keeps_saturday_14_to_18(self):
        cfg = load_config()['general']['tournament']
        first = occurrence_window(cfg, 0)
        second = occurrence_window(cfg, 1)
        for window in (first, second):
            start, end = (datetime.fromtimestamp(t, PARIS) for t in window)
            self.assertEqual((start.weekday(), start.hour, end.hour), (5, 14, 18))
        self.assertEqual(second[0] - first[0], 169 * 3600)

    def test_spring_forward_keeps_saturday_14_to_18(self):
        cfg = load_config()['general']['tournament']
        cfg.update(start_time=stamp(2027, 3, 27, 14), end_time=stamp(2027, 3, 27, 18))
        first, second = occurrence_window(cfg, 0), occurrence_window(cfg, 1)
        self.assertEqual(second[0] - first[0], 167 * 3600)
        self.assertEqual([datetime.fromtimestamp(t, PARIS).hour for t in second], [14, 18])

    def test_scheduler_uses_local_calendar_index_and_does_not_shift_next_saturday(self):
        cfg = load_config()
        now = stamp(2026, 10, 31, 13)
        with tempfile.TemporaryDirectory() as tmp, patch('backend.tournaments.time.time', return_value=now):
            service = Service(Path(tmp) / 'state.sqlite', cfg)
            service.stopping.set()
            service.maintenance.join()
            try:
                with service.store.transaction():
                    service.schedule_tournaments()
                    settings = service.tournament_config(2)
                    self.assertEqual(settings['start_time'], stamp(2026, 10, 31, 14))
                    self.assertEqual(settings['end_time'], stamp(2026, 10, 31, 18))
                    next_start = service.tournament_config(3)['start_time']
                    service.shift_upcoming_tournaments(2, settings['end_time'] + 86400)
                    self.assertEqual(service.tournament_config(3)['start_time'], next_start)
                result = service.public_tournaments()
                self.assertEqual(result['tournaments'][0]['phase'], 'upcoming')
                self.assertEqual(result['tournaments'][0]['start_time'], stamp(2026, 10, 31, 14))
            finally:
                service.close()
