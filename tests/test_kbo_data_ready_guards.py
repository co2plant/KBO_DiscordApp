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

    def test_update_tables_uses_kst_date_for_schedule_refresh(self):
        tree = _read_ast('kbo.py')
        update_tables = _find_function(tree, 'update_tables')

        saw_datetime_today = False
        saw_kst_now = False

        for node in ast.walk(update_tables):
            if not isinstance(node, ast.Call):
                continue

            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                if node.func.value.id == 'datetime' and node.func.attr == 'today':
                    saw_datetime_today = True

                if node.func.value.id == 'datetime' and node.func.attr == 'now':
                    if len(node.args) == 1 and isinstance(node.args[0], ast.Name) and node.args[0].id == 'KST':
                        saw_kst_now = True

        self.assertFalse(saw_datetime_today, 'update_tables should not use host-local datetime.today()')
        self.assertTrue(saw_kst_now, 'update_tables should use datetime.now(KST) for schedule refresh')


if __name__ == '__main__':
    unittest.main()
