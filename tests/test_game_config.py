import json
from pathlib import Path
import tempfile
import unittest

from tools.game_config import ConfigError, ROOT, load_config, resolve_stadium, startup_source


class GameConfigTests(unittest.TestCase):
    def test_tournament_entry_windows_cannot_overlap_or_run_backwards(self):
        self.assert_invalid(lambda c: c['general']['tournament'].update(repeat_seconds=1))
        self.assert_invalid(lambda c: c['general']['tournament'].update(end_time=0))

    def test_tournament_rotation_and_rewards_must_have_valid_assets(self):
        self.assert_invalid(lambda c: c['general']['tournament'].update(stadium_rotation=[10]))
        self.assert_invalid(lambda c: c['general']['tournament'].update(rewards=[1,2,3,99]))

    def test_knockout_rounds_fit_duration_and_capacity(self):
        self.assert_invalid(lambda c: c['general']['tournament'].update(
            qualification_seconds=c['general']['tournament']['end_time'] - c['general']['tournament']['start_time']))
        self.assert_invalid(lambda c: c['general']['tournament'].update(qualifying_top=8,round_count=2))

    def test_leagues_have_unique_ids_and_monotonic_thresholds(self):
        self.assert_invalid(lambda c: c['general']['progression']['leagues'][0].update(id=1))
        self.assert_invalid(lambda c: c['general']['progression']['leagues'][0].update(min_rating=1500))

    def test_stadium_overrides_preserve_other_rules_and_are_independent(self):
        config = load_config()
        kara = resolve_stadium(config, "KARA")
        self.assertEqual(kara["match"]["turns_per_match"], 14)
        self.assertEqual(kara["match"]["class_ability_uses"], 2)
        self.assertEqual(kara["match"]["planning_seconds"], 100)
        kara["simulation"]["ball"]["base_range"] = 100
        self.assertEqual(resolve_stadium(config, "BONTA")["simulation"]["ball"]["base_range"], 7)

    def assert_invalid(self, change):
        config = load_config()
        change(config)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            path.write_text(json.dumps(config))
            with self.assertRaises(ConfigError):
                load_config(path)

    def test_typo_in_stadium_override_is_rejected(self):
        self.assert_invalid(lambda c: c["stadiums"]["BONTA"]["overrides"].update(
            {"match": {"turn_per_match": 10}}))

    def test_invalid_effective_stadium_rule_is_rejected(self):
        self.assert_invalid(lambda c: c["stadiums"]["BONTA"]["overrides"].update(
            {"match": {"turns_per_match": 5}}))

    def test_invalid_probability_interval_is_rejected(self):
        self.assert_invalid(lambda c: c["rules"]["simulation"]["simulation"].update(
            {"probability_min": 0.9, "probability_max": 0.1}))

    def test_ball_exclusion_cannot_remove_entire_placement_zone(self):
        self.assert_invalid(lambda c: c["rules"]["simulation"]["placement"].update(
            {"ball_exclusion_radius_cells": 10}))

    def test_boolean_cannot_be_used_as_a_turn_count(self):
        self.assert_invalid(lambda c: c["rules"]["match"].update({"turns_per_match": True}))

    def test_desktop_and_android_generate_custom_classes_and_stadiums(self):
        config = load_config()
        config["rules"]["classes"]["overrides"]["IOP"].update({"earth": 19, "role": 1})
        config["stadiums"]["BEACH"]["enabled"] = False
        for path in ("patches/StartUpApplicationCommand.as", "android/patches/StartUpApplicationCommand.as"):
            generated = startup_source((ROOT / path).read_text(), config)
            self.assertIn("if(classId == 6) return new BoufbowlerAttributesModel(19,8,9,8,16,3);", generated)
            self.assertIn("rules.setMaxTurnDuration(6,14);", generated)
            self.assertIn("rules.setClassOrderUseByMatch(6,2);", generated)
            enabled = next(line for line in generated.splitlines() if ") stadiums.addItem" in line)
            self.assertNotIn("i == 3", enabled)
            self.assertNotIn("new BoufbowlerAttributesModel(12,10,10,10,16,3)))", generated)


if __name__ == "__main__":
    unittest.main()
