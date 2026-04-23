import ast
import unittest
from pathlib import Path
from typing import cast


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


class TestStandingsRendering(unittest.TestCase):
    def test_rank_emoji_supports_ten_teams(self):
        tree = _read_ast('kbo.py')

        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == 'emoji':
                        self.assertIsInstance(node.value, ast.List)
                        emoji_list = cast(ast.List, node.value)
                        self.assertGreaterEqual(len(emoji_list.elts), 11)
                        return

        raise AssertionError('emoji list assignment not found')

    def test_standings_uses_team_name_for_logo_lookup(self):
        tree = _read_ast('kbo.py')
        standings = _find_function(tree, 'standings')

        for node in ast.walk(standings):
            if not isinstance(node, ast.Subscript):
                continue
            if not isinstance(node.value, ast.Name) or node.value.id != 'logo_emoji':
                continue
            if not isinstance(node.slice, ast.Subscript):
                continue

            inner = node.slice
            if not isinstance(inner.value, ast.Subscript):
                continue
            if not isinstance(inner.value.value, ast.Name) or inner.value.value.id != 'from_db_result':
                continue
            if not isinstance(inner.slice, ast.Constant):
                continue

            self.assertNotEqual(inner.slice.value, 2, 'standings must not use win column for logo lookup')

    def test_standings_uses_single_non_inline_field(self):
        tree = _read_ast('kbo.py')
        standings = _find_function(tree, 'standings')

        field_names = []
        inline_values = []
        add_field_calls = 0

        for node in ast.walk(standings):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute) or node.func.attr != 'add_field':
                continue

            add_field_calls += 1

            for keyword in node.keywords:
                if keyword.arg == 'name' and isinstance(keyword.value, ast.Constant):
                    field_names.append(keyword.value.value)
                if keyword.arg == 'inline' and isinstance(keyword.value, ast.Constant):
                    inline_values.append(keyword.value.value)

        self.assertEqual(field_names, ['전체 순위'])
        self.assertEqual(add_field_calls, 1)
        self.assertEqual(inline_values, [False])

    def test_standings_no_longer_uses_rank_band_labels(self):
        tree = _read_ast('kbo.py')
        standings = _find_function(tree, 'standings')

        joined_constants = []
        for node in ast.walk(standings):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                joined_constants.append(node.value)

        rendered_text = ''.join(joined_constants)
        self.assertNotIn('1-3위', rendered_text)
        self.assertNotIn('4-6위', rendered_text)
        self.assertNotIn('7-10위', rendered_text)

    def test_standings_line_includes_all_core_stats(self):
        tree = _read_ast('kbo.py')
        standings = _find_function(tree, 'standings')

        joined_constants = []
        for node in ast.walk(standings):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                joined_constants.append(node.value)

        rendered_text = ''.join(joined_constants)
        self.assertIn('순위 | 팀 | 승 | 패 | 무 | 승률', rendered_text)
        self.assertIn(' | ', rendered_text)

    def test_standings_summary_omits_detail_stats(self):
        tree = _read_ast('kbo.py')
        standings = _find_function(tree, 'standings')

        joined_constants = []
        for node in ast.walk(standings):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                joined_constants.append(node.value)

        rendered_text = ''.join(joined_constants)
        self.assertNotIn('최근10 ', rendered_text)
        self.assertNotIn('홈 ', rendered_text)
        self.assertNotIn('방문 ', rendered_text)
        self.assertNotIn('연속', rendered_text)

    def test_standings_summary_labels_are_explicit(self):
        tree = _read_ast('kbo.py')
        standings = _find_function(tree, 'standings')

        joined_constants = []
        for node in ast.walk(standings):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                joined_constants.append(node.value)

        rendered_text = ''.join(joined_constants)
        self.assertIn('순위 | 팀 | 승 | 패 | 무 | 승률', rendered_text)

    def test_is_hot_streak_only_marks_three_or_more_wins(self):
        is_hot_streak = _load_function('kbo.py', '_is_hot_streak')

        self.assertTrue(is_hot_streak('3승'))
        self.assertTrue(is_hot_streak('4승'))
        self.assertFalse(is_hot_streak('2승'))
        self.assertFalse(is_hot_streak('1패'))

    def test_standings_fire_emoji_is_present_in_summary_format(self):
        tree = _read_ast('kbo.py')
        standings = _find_function(tree, 'standings')

        joined_constants = []
        for node in ast.walk(standings):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                joined_constants.append(node.value)

        self.assertIn(' 🔥', ''.join(joined_constants))

    def test_team_standings_command_exists(self):
        tree = _read_ast('kbo.py')
        team_standings = _find_function(tree, 'team_standings')

        decorator_names = []
        for decorator in team_standings.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not isinstance(decorator.func, ast.Attribute):
                continue
            decorator_names.append(decorator.func.attr)

        self.assertIn('command', decorator_names)
        self.assertIn('describe', decorator_names)

    def test_team_standings_embed_includes_moved_detail_stats(self):
        tree = _read_ast('kbo.py')
        team_standings = _find_function(tree, 'team_standings')

        joined_constants = []
        for node in ast.walk(team_standings):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                joined_constants.append(node.value)

        rendered_text = ''.join(joined_constants)
        self.assertIn('최근 10경기', rendered_text)
        self.assertIn('연속', rendered_text)
        self.assertIn('홈', rendered_text)
        self.assertIn('원정', rendered_text)

    def test_team_standings_handles_missing_team_cleanly(self):
        tree = _read_ast('kbo.py')
        team_standings = _find_function(tree, 'team_standings')

        missing_team_message_found = False
        for node in ast.walk(team_standings):
            if isinstance(node, ast.Constant) and node.value == ' 팀의 성적을 찾을 수 없습니다.':
                missing_team_message_found = True

        self.assertTrue(missing_team_message_found)

    def test_schedule_matchup_hides_negative_one_sentinel_scores(self):
        format_schedule_matchup = _load_function(
            'kbo.py',
            '_format_schedule_matchup',
            namespace={
                'datetime': object,
                'logo_emoji': {'한화': ':HH:', 'LG': ':LG:'},
                '_should_hide_schedule_score': lambda *_args: True,
            },
        )

        row = ('042200', '18:30', '한화', 'LG', '잠실', '-', -1, -1, -1)
        rendered = format_schedule_matchup(None, row)

        self.assertNotIn('-1', rendered)
        self.assertIn('vs', rendered)


if __name__ == '__main__':
    unittest.main()
