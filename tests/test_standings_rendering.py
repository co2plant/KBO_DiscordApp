import ast
import unittest
from pathlib import Path
from typing import cast


def _read_ast(path: str) -> ast.Module:
    source = Path(path).read_text(encoding='utf-8')
    return ast.parse(source, filename=path)


def _find_function(tree: ast.Module, name: str) -> ast.AsyncFunctionDef:
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name:
            return node
    raise AssertionError(f'{name} function not found')


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

    def test_standings_uses_sectioned_non_inline_fields(self):
        tree = _read_ast('kbo.py')
        standings = _find_function(tree, 'standings')

        section_names = []
        inline_values = []
        add_field_calls = 0

        for node in ast.walk(standings):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if not isinstance(target, ast.Name) or target.id != 'section_ranges':
                        continue
                    self.assertIsInstance(node.value, ast.List)
                    section_ranges = cast(ast.List, node.value)
                    for element in section_ranges.elts:
                        self.assertIsInstance(element, ast.Tuple)
                        section_tuple = cast(ast.Tuple, element)
                        self.assertIsInstance(section_tuple.elts[0], ast.Constant)
                        section_name = cast(ast.Constant, section_tuple.elts[0])
                        section_names.append(section_name.value)

            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute) or node.func.attr != 'add_field':
                continue

            add_field_calls += 1

            for keyword in node.keywords:
                if keyword.arg == 'inline' and isinstance(keyword.value, ast.Constant):
                    inline_values.append(keyword.value.value)

        self.assertEqual(section_names, ['1-3위', '4-6위', '7-10위'])
        self.assertEqual(add_field_calls, 1)
        self.assertEqual(inline_values, [False])

    def test_standings_line_includes_all_core_stats(self):
        tree = _read_ast('kbo.py')
        standings = _find_function(tree, 'standings')

        joined_constants = []
        for node in ast.walk(standings):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                joined_constants.append(node.value)

        self.assertIn('승 ', ''.join(joined_constants))
        self.assertIn('패 ', ''.join(joined_constants))
        self.assertIn('무 (', ''.join(joined_constants))

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


if __name__ == '__main__':
    unittest.main()
