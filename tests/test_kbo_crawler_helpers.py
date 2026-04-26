import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class _DatabaseModule(types.ModuleType):
    pass


class _WebDriverModule(types.ModuleType):
    class ChromeOptions:
        def add_argument(self, _argument):
            return None

    def Chrome(self, _options):
        return None


class _SeleniumModule(types.ModuleType):
    webdriver: _WebDriverModule


class _ByModule(types.ModuleType):
    By: object


def _load_kbo_crawler_with_stubs():
    webdriver_module = _WebDriverModule('selenium.webdriver')
    selenium_module = _SeleniumModule('selenium')
    selenium_module.webdriver = webdriver_module
    by_module = _ByModule('selenium.webdriver.common.by')
    by_module.By = types.SimpleNamespace(XPATH='xpath', TAG_NAME='tag_name', CLASS_NAME='class_name')

    with patch.dict(
        sys.modules,
        {
            'database': _DatabaseModule('database'),
            'selenium': selenium_module,
            'selenium.webdriver': webdriver_module,
            'selenium.webdriver.common': types.ModuleType('selenium.webdriver.common'),
            'selenium.webdriver.common.by': by_module,
        },
    ):
        spec = importlib.util.spec_from_file_location('kbo_crawler_under_test', Path('kbo_crawler.py'))
        if spec is None or spec.loader is None:
            raise AssertionError('failed to load kbo_crawler.py')

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


class TestKboCrawlerHelpers(unittest.TestCase):
    def test_split_matchup_text_extracts_teams_and_scores(self):
        kbo_crawler = _load_kbo_crawler_with_stubs()

        team, score = kbo_crawler._split_matchup_text('한화3vs2LG')

        self.assertEqual(team, ['한화', 'LG'])
        self.assertEqual(score, ['3', '2'])

    def test_split_matchup_text_preserves_empty_scores(self):
        kbo_crawler = _load_kbo_crawler_with_stubs()

        team, score = kbo_crawler._split_matchup_text('한화vsLG')

        self.assertEqual(team, ['한화', 'LG'])
        self.assertEqual(score, ['', ''])


if __name__ == '__main__':
    unittest.main()
