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
        player_situational_stats = _find_function(tree, 'player_situational_stats')
        team_situational_stats = _find_function(tree, 'team_situational_stats')
        compare_player_situational_stats = _find_function(tree, 'compare_player_situational_stats')

        self.assertTrue(_has_awaited_name_call(standings, 'ensure_data_ready'))
        self.assertTrue(_has_awaited_name_call(team_standings, 'ensure_data_ready'))
        self.assertTrue(_has_awaited_name_call(schedule, 'ensure_data_ready'))
        self.assertTrue(_has_awaited_name_call(player_situational_stats, 'ensure_data_ready'))
        self.assertTrue(_has_awaited_name_call(team_situational_stats, 'ensure_data_ready'))
        self.assertTrue(_has_awaited_name_call(compare_player_situational_stats, 'ensure_data_ready'))

    def test_ensure_data_ready_registers_initial_situational_refresh(self):
        tree = _read_ast('kbo.py')
        ensure_data_ready = _find_function(tree, 'ensure_data_ready')

        saw_refresh_call = False
        for node in ast.walk(ensure_data_ready):
            if not isinstance(node, ast.Attribute):
                continue
            if isinstance(node.value, ast.Name) and node.value.id == 'kbo_crawler':
                if node.attr == 'refresh_situational_stats_if_stale':
                    saw_refresh_call = True

        self.assertTrue(saw_refresh_call, 'startup data readiness must trigger initial situational refresh')

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

    def test_update_tables_registers_situational_refresh(self):
        tree = _read_ast('kbo.py')
        update_tables = _find_function(tree, 'update_tables')

        saw_refresh_call = False
        for node in ast.walk(update_tables):
            if not isinstance(node, ast.Attribute):
                continue
            if isinstance(node.value, ast.Name) and node.value.id == 'kbo_crawler':
                if node.attr == 'refresh_situational_stats_if_stale':
                    saw_refresh_call = True

        self.assertTrue(saw_refresh_call, 'scheduled refresh must include situational stats refresh')


class TestSituationalRefreshGuards(unittest.TestCase):
    def test_situational_commands_do_not_call_crawler(self):
        tree = _read_ast('kbo.py')
        command_names = (
            'player_situational_stats',
            'team_situational_stats',
            'compare_player_situational_stats',
        )

        for command_name in command_names:
            command = _find_function(tree, command_name)
            for node in ast.walk(command):
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                    self.assertNotEqual(node.value.id, 'kbo_crawler', f'{command_name} must not call crawler helpers')

    def test_situational_commands_use_database_helpers(self):
        tree = _read_ast('kbo.py')
        expected_helpers = {
            'player_situational_stats': {'get_player_situational_stats'},
            'team_situational_stats': {'get_team_situational_aggregate', 'get_team_situational_leaders'},
            'compare_player_situational_stats': {'get_player_situational_stats'},
        }

        for command_name, helper_names in expected_helpers.items():
            command = _find_function(tree, command_name)
            called_helpers = set()
            for node in ast.walk(command):
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == 'database':
                    called_helpers.add(node.attr)
            self.assertTrue(helper_names.issubset(called_helpers))

    def test_team_situational_command_resolves_team_alias(self):
        tree = _read_ast('kbo.py')
        command = _find_function(tree, 'team_situational_stats')

        saw_alias_resolver = False
        for node in ast.walk(command):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == 'resolve_situational_team_input':
                    saw_alias_resolver = True

        self.assertTrue(saw_alias_resolver)


if __name__ == '__main__':
    unittest.main()
