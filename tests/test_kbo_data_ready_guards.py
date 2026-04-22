import ast
import unittest
from pathlib import Path


def _read_ast(path: str) -> ast.Module:
    source = Path(path).read_text(encoding='utf-8')
    return ast.parse(source, filename=path)


def _find_function(tree: ast.Module, name: str):
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f'{name} function not found')


def _has_awaited_name_call(function_node: ast.FunctionDef | ast.AsyncFunctionDef, target_name: str) -> bool:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Await):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        if isinstance(node.value.func, ast.Name) and node.value.func.id == target_name:
            return True
    return False


class TestKboDataReadyGuards(unittest.TestCase):
    def test_ensure_data_ready_exists(self):
        tree = _read_ast('kbo.py')
        ensure_data_ready = _find_function(tree, 'ensure_data_ready')
        self.assertIsInstance(ensure_data_ready, ast.AsyncFunctionDef)

    def test_on_ready_awaits_data_ready(self):
        tree = _read_ast('kbo.py')
        on_ready = _find_function(tree, 'on_ready')
        self.assertTrue(_has_awaited_name_call(on_ready, 'ensure_data_ready'))

    def test_data_commands_await_data_ready(self):
        tree = _read_ast('kbo.py')
        standings = _find_function(tree, 'standings')
        team_standings = _find_function(tree, 'team_standings')
        schedule = _find_function(tree, 'schedule')

        self.assertTrue(_has_awaited_name_call(standings, 'ensure_data_ready'))
        self.assertTrue(_has_awaited_name_call(team_standings, 'ensure_data_ready'))
        self.assertTrue(_has_awaited_name_call(schedule, 'ensure_data_ready'))


if __name__ == '__main__':
    unittest.main()
