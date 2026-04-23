import ast
import importlib.util
import sys
import types
import unittest
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch


def _read_ast(path: str) -> ast.Module:
    source = Path(path).read_text(encoding='utf-8')
    return ast.parse(source, filename=path)


def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f'{name} function not found')


def _has_driver_quit_in_finally(function_node: ast.FunctionDef) -> bool:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Try):
            continue

        for final_node in node.finalbody:
            for child in ast.walk(final_node):
                if not isinstance(child, ast.Call):
                    continue
                if not isinstance(child.func, ast.Attribute):
                    continue
                if not isinstance(child.func.value, ast.Name):
                    continue
                if child.func.value.id == 'driver' and child.func.attr == 'quit':
                    return True

    return False


class _FakeTextNode:
    def __init__(self, text: str):
        self.text = text


class _FakeRow:
    def find_elements(self, by, value):
        return [
            _FakeTextNode('1'),
            _FakeTextNode('두산'),
            _FakeTextNode('10'),
            _FakeTextNode('5'),
            _FakeTextNode('1'),
            _FakeTextNode('unused'),
            _FakeTextNode('0.667'),
            _FakeTextNode('unused'),
            _FakeTextNode('7-3'),
            _FakeTextNode('2연승'),
            _FakeTextNode('5-2'),
            _FakeTextNode('5-3'),
        ]


class _FakeDriver:
    def __init__(self):
        self.quit_calls = 0

    def get(self, url):
        self.url = url

    def find_elements(self, by, value):
        return [_FakeRow()]

    def quit(self):
        self.quit_calls += 1


class _FakeChromeOptions:
    def __init__(self):
        self.arguments = []

    def add_argument(self, argument):
        self.arguments.append(argument)


class _DatabaseModule(types.ModuleType):
    insert_standings: Callable[[object], None]
    update_standings: Callable[[object], None]
    update_game_and_score: Callable[[object], None]
    insert_game_and_score: Callable[[object], None]


class _WebDriverModule(types.ModuleType):
    ChromeOptions: type[_FakeChromeOptions]
    Chrome: Callable[[object], _FakeDriver]


class _SeleniumModule(types.ModuleType):
    webdriver: _WebDriverModule


class _ByModule(types.ModuleType):
    By: object


def _load_kbo_crawler_with_stubs(driver_holder: dict):
    fake_database = _DatabaseModule('database')

    def insert_standings(_game_info):
        raise RuntimeError('forced database failure')

    fake_database.insert_standings = insert_standings
    fake_database.update_standings = lambda _game_info: None
    fake_database.update_game_and_score = lambda _game_info: None
    fake_database.insert_game_and_score = lambda _game_info: None

    webdriver_module = _WebDriverModule('selenium.webdriver')
    webdriver_module.ChromeOptions = _FakeChromeOptions

    def create_driver(_options):
        driver = _FakeDriver()
        driver_holder['driver'] = driver
        return driver

    webdriver_module.Chrome = create_driver

    selenium_module = _SeleniumModule('selenium')
    selenium_module.webdriver = webdriver_module

    by_module = _ByModule('selenium.webdriver.common.by')
    by_module.By = types.SimpleNamespace(XPATH='xpath', TAG_NAME='tag_name', CLASS_NAME='class_name')

    with patch.dict(
        sys.modules,
        {
            'database': fake_database,
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


class TestCrawlerCleanup(unittest.TestCase):
    def test_driver_quit_is_guaranteed_in_all_driver_functions(self):
        tree = _read_ast('kbo_crawler.py')

        for function_name in [
            'insert_standings',
            'update_standings',
            'update_schedule_once',
            'update_score',
            'insert_schedule_month',
        ]:
            function_node = _find_function(tree, function_name)
            self.assertTrue(
                _has_driver_quit_in_finally(function_node),
                f'{function_name} must quit the driver in a finally block',
            )

    def test_insert_standings_quits_driver_on_database_failure(self):
        driver_holder = {}
        module = _load_kbo_crawler_with_stubs(driver_holder)

        with self.assertRaisesRegex(RuntimeError, 'forced database failure'):
            module.insert_standings()

        self.assertIn('driver', driver_holder, 'test should create a webdriver instance')
        self.assertEqual(driver_holder['driver'].quit_calls, 1, 'driver.quit() must run on failure')


if __name__ == '__main__':
    unittest.main()
