import ast
import unittest
from pathlib import Path


def _read_ast(path: str) -> ast.Module:
    source = Path(path).read_text(encoding='utf-8')
    return ast.parse(source, filename=path)


def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f'{name} function not found')


def _load_function(path: str, name: str, namespace=None):
    tree = _read_ast(path)
    function_node = _find_function(tree, name)
    module = ast.Module(body=[function_node], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {} if namespace is None else dict(namespace)
    exec(compile(module, path, 'exec'), namespace)
    return namespace[name]


def _command_name(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    for decorator in function_node.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        if not isinstance(decorator.func, ast.Attribute):
            continue
        if decorator.func.attr != 'command':
            continue
        for keyword in decorator.keywords:
            if keyword.arg == 'name' and isinstance(keyword.value, ast.Constant):
                return keyword.value.value
    return None


def _awaits_helper(function_node: ast.FunctionDef | ast.AsyncFunctionDef, helper_name: str) -> bool:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Await):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        call = node.value
        if isinstance(call.func, ast.Name) and call.func.id == helper_name:
            return True
    return False


class TestScoreTeamCommands(unittest.TestCase):
    def test_score_command_exists(self):
        tree = _read_ast('kbo.py')
        scores = _find_function(tree, 'scores')

        self.assertEqual(_command_name(scores), '스코어')
        self.assertTrue(_awaits_helper(scores, '_ensure_schedule_data_for_date'))

    def test_team_summary_command_exists(self):
        tree = _read_ast('kbo.py')
        team_summary = _find_function(tree, 'team_summary')

        self.assertEqual(_command_name(team_summary), '팀')
        self.assertTrue(_awaits_helper(team_summary, '_ensure_schedule_data_for_date'))
        self.assertTrue(_awaits_helper(team_summary, '_refresh_standings_for_command'))

    def test_format_score_line_hides_sentinel_scores_before_game(self):
        format_score_line = _load_function(
            'kbo.py',
            '_format_score_line',
            namespace={
                'datetime': object,
                'logo_emoji': {'LG': ':LG:', '한화': ':HH:'},
                '_should_hide_schedule_score': lambda *_args: True,
            },
        )

        row = ('050400', '18:30', 'LG', '한화', '잠실', '-', '050400', -1, -1)
        rendered = format_score_line(None, row)

        self.assertIn('18:30', rendered)
        self.assertIn(':LG: LG vs :HH: 한화', rendered)
        self.assertIn('잠실', rendered)
        self.assertIn('경기 전', rendered)
        self.assertNotIn('-1', rendered)

    def test_format_score_line_includes_current_score(self):
        format_score_line = _load_function(
            'kbo.py',
            '_format_score_line',
            namespace={
                'datetime': object,
                'logo_emoji': {'LG': ':LG:', '한화': ':HH:'},
                '_should_hide_schedule_score': lambda *_args: False,
            },
        )

        row = ('050400', '18:30', 'LG', '한화', '잠실', '-', '050400', 3, 2)
        rendered = format_score_line(None, row)

        self.assertIn(':LG: LG 3 vs 2 :HH: 한화', rendered)
        self.assertIn('진행/종료', rendered)

    def test_find_team_games_matches_home_and_away_case_insensitively(self):
        find_team_games = _load_function(
            'kbo.py',
            '_find_team_games',
            namespace={'_normalize_team_name': lambda team_name: team_name.strip().upper()},
        )

        rows = [
            ('050400', '18:30', 'LG', '한화', '잠실', '-', '050400', 3, 2),
            ('050401', '18:30', 'KIA', '두산', '광주', '-', '050401', 1, 4),
            ('050402', '18:30', 'KT', 'LG', '수원', '-', '050402', 5, 5),
        ]

        result = find_team_games(rows, 'lg')

        self.assertEqual([row[0] for row in result], ['050400', '050402'])


if __name__ == '__main__':
    unittest.main()
