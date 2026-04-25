import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


def _load_crawler_module():
    fake_database = types.ModuleType('database')
    fake_selenium = types.ModuleType('selenium')
    fake_webdriver = types.ModuleType('selenium.webdriver')
    fake_common = types.ModuleType('selenium.webdriver.common')
    fake_by = types.ModuleType('selenium.webdriver.common.by')

    class _By:
        XPATH = 'xpath'
        TAG_NAME = 'tag name'
        CLASS_NAME = 'class name'

    setattr(fake_by, 'By', _By)
    setattr(fake_webdriver, 'ChromeOptions', object)
    setattr(fake_webdriver, 'Chrome', object)
    setattr(fake_selenium, 'webdriver', fake_webdriver)

    with patch.dict(sys.modules, {
        'database': fake_database,
        'selenium': fake_selenium,
        'selenium.webdriver': fake_webdriver,
        'selenium.webdriver.common': fake_common,
        'selenium.webdriver.common.by': fake_by,
    }):
        spec = importlib.util.spec_from_file_location('kbo_crawler_under_test', Path('kbo_crawler.py'))
        if spec is None or spec.loader is None:
            raise AssertionError('failed to load kbo_crawler.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


def _fixture(name):
    return Path('tests/fixtures', name).read_text(encoding='utf-8')


class TestSituationalSourceFixtures(unittest.TestCase):
    def test_hitter_runner_state_fixture_shape(self):
        html = _fixture('kbo_hitter_situations_runner_67341.html')

        self.assertIn('<table', html)
        self.assertIn('<tr', html)
        for label in ('RUNNER', 'AVG', 'AB', 'H', '2B', '3B', 'HR', 'RBI', 'BB', 'HBP', 'SO', 'GIDP'):
            self.assertIn(label, html)
        for runner_label in ('BASES EMPTY', 'ONLY 1st BASE', 'BASED ON LOADED'):
            self.assertIn(runner_label, html)

    def test_hitter_summary_fixture_profile_shape(self):
        html = _fixture('kbo_hitter_summary_67341.html')

        for label in ('Name', 'Position', 'No', 'Salary', 'Born', 'Debut', 'HT/WT', 'Transaction'):
            self.assertIn(label, html)
        self.assertIn('KIWOOM HEROES', html)
        self.assertIn('pcode=67341', html)

    def test_team_runner_state_source_decision(self):
        html = _fixture('kbo_batting_by_teams.html')

        self.assertIn('TEAM', html)
        self.assertNotIn('RUNNER', html)
        self.assertNotIn('BASED ON LOADED', html)


class TestRunnerStateNormalization(unittest.TestCase):
    def test_phase1_runner_labels_normalize(self):
        crawler = _load_crawler_module()

        expected = {
            'BASES EMPTY': 'bases_empty',
            'RUNNERS ON': 'runners_on',
            'ONLY 1st BASE': 'runner_on_1',
            'ONLY 2nd BASE': 'runner_on_2',
            'ONLY 3rd BASE': 'runner_on_3',
            '1st + 2nd BASE': 'runner_on_1_2',
            '1st + 3rd BASE': 'runner_on_1_3',
            '2nd + 3rd BASE': 'runner_on_2_3',
            'BASED ON LOADED': 'bases_loaded',
            'SCORING POSITION': 'scoring_position',
        }
        for label, split_key in expected.items():
            self.assertEqual(crawler.normalize_runner_state_label(label), split_key)
        self.assertEqual(crawler.normalize_runner_state_label(' bases empty '), 'bases_empty')
        self.assertIsNone(crawler.normalize_runner_state_label('UNKNOWN'))


class TestPlayerProfileParser(unittest.TestCase):
    def test_parse_player_profile_from_summary_fixture(self):
        crawler = _load_crawler_module()
        profile = crawler.parse_player_profile(_fixture('kbo_hitter_summary_67341.html'), '67341')

        self.assertEqual(profile['player_id'], '67341')
        self.assertEqual(profile['team_name'], 'KIWOOM HEROES')
        self.assertEqual(profile['name'], 'LEE Jung Hoo')
        self.assertEqual(profile['position'], 'Outfielder')
        self.assertEqual(profile['born'], '20/08/1998')
        self.assertEqual(profile['height_weight'], '185cm/86kg')
        self.assertEqual(profile['salary'], '￦ 1,100,000,000')
        self.assertEqual(profile['debut'], '17')
        self.assertIsNotNone(profile['updated_at'])


class TestRunnerStateParser(unittest.TestCase):
    def test_parse_runner_state_rows_from_fixture(self):
        crawler = _load_crawler_module()
        rows = crawler.parse_runner_state_stats(
            _fixture('kbo_hitter_situations_runner_67341.html'),
            player_id='67341',
            team_name='Kiwoom',
            season=2026,
            source_updated_at='2026-04-24 00:00:00',
        )

        split_keys = {row['split_key'] for row in rows}
        self.assertIn('bases_empty', split_keys)
        self.assertIn('runner_on_1', split_keys)
        self.assertIn('bases_loaded', split_keys)
        bases_loaded = next(row for row in rows if row['split_key'] == 'bases_loaded')
        self.assertEqual(bases_loaded['split_type'], 'runner_state')
        self.assertEqual(bases_loaded['ab'], 3)
        self.assertEqual(bases_loaded['h'], 1)
        self.assertEqual(bases_loaded['hr'], 1)
        self.assertEqual(bases_loaded['pa'], 4)
        self.assertEqual(bases_loaded['obp'], 0.5)
        self.assertEqual(bases_loaded['slg'], 1.333)
        self.assertEqual(bases_loaded['ops'], 1.833)

    def test_refresh_situational_stats_if_stale_uses_freshness_guard(self):
        crawler = _load_crawler_module()
        calls = []

        class _FakeDatabase:
            def should_refresh_situational_stats(self, _now):
                calls.append('checked')
                return False

        setattr(crawler, 'database', _FakeDatabase())
        refreshed = crawler.refresh_situational_stats_if_stale(2026)

        self.assertFalse(refreshed)
        self.assertEqual(calls, ['checked'])


class TestPlayerDiscovery(unittest.TestCase):
    def test_discovers_hitter_player_ids_from_fixture(self):
        crawler = _load_crawler_module()
        player_ids = crawler.discover_hitter_player_ids(_fixture('kbo_batting_by_teams.html'))

        self.assertEqual(player_ids, ['67341', '50054'])
        self.assertTrue(all(player_id.isdigit() for player_id in player_ids))


if __name__ == '__main__':
    unittest.main()
