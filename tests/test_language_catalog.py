"""Validate the legacy JSON-with-comments catalog and resource regeneration."""
from collections import Counter
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from tools.game_config import ROOT, apply_resources, load_config
from tools.tournament_text import replace_translation_block


TOKENS = r'"(?:\\.|[^"\\])*"|/\*[\s\S]*?\*/|//[^\n]*'


def comments(text):
    return Counter(m[0] for m in re.finditer(TOKENS, text) if not m[0].startswith('"'))


def catalog(text):
    text = re.sub(TOKENS, lambda m: m[0] if m[0].startswith('"') else '\n' * m[0].count('\n'), text)
    text = re.sub(r'"(?:\\.|[^"\\])*"|,\s*(?=[}\]])', lambda m: m[0] if m[0].startswith('"') else m[0][1:], text)
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate translation key: ' + key)
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=unique)


class LanguageCatalogTests(unittest.TestCase):
    def test_catalog_and_repeated_resource_builds_preserve_structure_and_comments(self):
        original = (ROOT / 'resources/lang.json').read_text()
        initial = catalog(original)
        for key in ('tournament_help_content', 'tournament_elimination_rule',
                    'tournament_tournament_type_enum', 'tournament_rewards_desc',
                    'tournament_past_tournament_button', 'tournament_future_tournament_button'):
            self.assertEqual(set(initial[key]), {'fr', 'en', 'de', 'es'})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'lang.json'
            path.write_text(original)
            (Path(directory) / 'config.json').write_text((ROOT / 'resources/config.json').read_text())
            with patch('tools.visual_assets.prepare_stadiums', return_value={}):
                for _ in range(3):
                    apply_resources(Path(directory), load_config())
                    generated = path.read_text()
                    self.assertEqual(set(catalog(generated)), set(initial))
                    self.assertEqual(comments(generated), comments(original))

    def test_block_replacement_ignores_indentation_quotes_and_commented_braces(self):
        source = '{"help": { /* } */ "fr": {"nested": "a } brace"}}, "next": {"fr":"kept"}}'
        updated = replace_translation_block(source, 'help', {'fr': 'new'})
        self.assertEqual(catalog(updated), {'help': {'fr': 'new'}, 'next': {'fr': 'kept'}})
        self.assertEqual(comments(updated), comments(source))
        self.assertEqual(replace_translation_block(updated, 'help', {'fr': 'new'}), updated)
