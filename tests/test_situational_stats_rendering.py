import ast
from collections.abc import Callable
from typing import Optional, cast
import unittest
from pathlib import Path


def _read_ast(path: str) -> ast.Module:
    source = Path(path).read_text(encoding='utf-8')
    return ast.parse(source, filename=path)


def _load_render_namespace():
    tree = _read_ast('kbo.py')
    wanted_names = {
        'VISIBLE_RUNNER_STATE_SPLIT_KEYS',
        'RUNNER_STATE_SPLIT_LABELS',
        'RUNNER_STATE_INPUT_ALIASES',
        'TEAM_SITUATIONAL_ALIASES',
    }
    wanted_functions = {
        'resolve_runner_state_input',
        'resolve_situational_team_input',
        '_normalize_team_name',
        '_format_rate',
        '_format_count',
        '_player_display_name',
        '_player_team_name',
        '_player_id',
        'build_player_situational_model',
        'build_team_situational_model',
        'build_player_comparison_model',
        '_describe_player_candidates',
        '_send_text',
    }
    body = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id in wanted_names for target in node.targets):
                body.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            body.append(node)
    module = ast.Module(body=body, type_ignores=[])
    ast.fix_missing_locations(module)
    namespace: dict[str, object] = {'Optional': Optional}
    exec(compile(module, 'kbo.py', 'exec'), namespace)
    return namespace


class TestSituationalSplitChoices(unittest.TestCase):
    def test_visible_phase1_split_keys(self):
        namespace = _load_render_namespace()

        visible = cast(tuple[str, ...], namespace['VISIBLE_RUNNER_STATE_SPLIT_KEYS'])
        self.assertEqual(visible, (
            'bases_empty',
            'runner_on_1',
            'runner_on_2',
            'runner_on_3',
            'runner_on_1_2',
            'runner_on_1_3',
            'runner_on_2_3',
            'bases_loaded',
            'scoring_position',
        ))

    def test_stored_but_hidden_split_keys_are_not_command_choices(self):
        namespace = _load_render_namespace()
        visible = cast(tuple[str, ...], namespace['VISIBLE_RUNNER_STATE_SPLIT_KEYS'])
        labels = cast(dict[str, str], namespace['RUNNER_STATE_SPLIT_LABELS'])

        for hidden in ('runners_on', 'on_first_any', 'on_second_any', 'on_third_any'):
            self.assertNotIn(hidden, visible)
        for split_key in visible:
            self.assertIn(split_key, labels)

    def test_korean_aliases_resolve_to_split_keys(self):
        namespace = _load_render_namespace()
        resolve = cast(Callable[[str], str | None], namespace['resolve_runner_state_input'])

        self.assertEqual(resolve('만루'), 'bases_loaded')
        self.assertEqual(resolve('득점권'), 'scoring_position')
        self.assertEqual(resolve('bases_empty'), 'bases_empty')
        self.assertIsNone(resolve('알수없음'))

    def test_team_aliases_resolve_to_official_situational_team_names(self):
        namespace = _load_render_namespace()
        resolve = cast(Callable[[str], str], namespace['resolve_situational_team_input'])

        self.assertEqual(resolve('KT'), 'KT WIZ')
        self.assertEqual(resolve('키움'), 'KIWOOM HEROES')
        self.assertEqual(resolve('lg'), 'LG TWINS')
        self.assertEqual(resolve('UNKNOWN TEAM'), 'UNKNOWN TEAM')


class TestSituationalCommandRendering(unittest.TestCase):
    def test_player_situational_embed_from_seeded_row(self):
        namespace = _load_render_namespace()
        build = cast(Callable[..., dict[str, object]], namespace['build_player_situational_model'])
        player = {'player_id': '67341', 'team_name': 'Kiwoom', 'name': 'LEE Jung Hoo'}
        stat = {'avg': 0.333, 'obp': 0.5, 'slg': 1.333, 'ops': 1.833, 'pa': 4, 'ab': 3, 'h': 1, 'hr': 1, 'rbi': 4}

        model = build(player, stat, '만루')

        self.assertIn('Kiwoom LEE Jung Hoo', cast(str, model['title']))
        fields = cast(list[tuple[str, str]], model['fields'])
        rendered = '\n'.join(value for _, value in fields)
        self.assertIn('만루', rendered)
        for label in ('AVG', 'OBP', 'SLG', 'OPS', 'PA', 'AB', 'H', 'HR', 'RBI'):
            self.assertIn(label, rendered)

    def test_text_reply_helper_suppresses_allowed_mentions(self):
        tree = _read_ast('kbo.py')
        send_text = None
        for node in tree.body:
            if isinstance(node, ast.AsyncFunctionDef) and node.name == '_send_text':
                send_text = node
                break
        if send_text is None:
            raise AssertionError('_send_text helper not found')

        rendered_constants = []
        saw_allowed_mentions_keyword = False
        saw_allowed_mentions_none_call = False
        for node in ast.walk(send_text):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                rendered_constants.append(node.value)
            if isinstance(node, ast.keyword) and node.arg == 'allowed_mentions':
                saw_allowed_mentions_keyword = True
                if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
                    saw_allowed_mentions_none_call = node.value.func.attr == 'none'

        self.assertTrue(saw_allowed_mentions_keyword)
        self.assertTrue(saw_allowed_mentions_none_call)

    def test_team_situational_embed_uses_player_aggregate_and_top_three(self):
        namespace = _load_render_namespace()
        build = cast(Callable[..., dict[str, object]], namespace['build_team_situational_model'])
        aggregate = {'avg': 0.5, 'ops': 1.375, 'pa': 10, 'ab': 8}
        leaders = [
            {'name': 'A', 'ops': 1.5, 'pa': 5, 'hr': 1, 'rbi': 3},
            {'name': 'B', 'ops': 1.0, 'pa': 4, 'hr': 0, 'rbi': 1},
            {'name': 'C', 'ops': 0.8, 'pa': 3, 'hr': 0, 'rbi': 1},
            {'name': 'D', 'ops': 0.7, 'pa': 2, 'hr': 0, 'rbi': 0},
        ]

        model = build('KT', aggregate, leaders, '만루')

        self.assertIn('KT', cast(str, model['title']))
        fields = cast(list[tuple[str, str]], model['fields'])
        rendered = '\n'.join(value for _, value in fields)
        self.assertIn('AVG', rendered)
        self.assertIn('OPS', rendered)
        self.assertIn('PA', rendered)
        self.assertIn('AB', rendered)
        self.assertIn('1. A', rendered)
        self.assertIn('2. B', rendered)
        self.assertIn('3. C', rendered)
        self.assertNotIn('4. D', rendered)

    def test_player_comparison_embed_uses_same_split_for_both_players(self):
        namespace = _load_render_namespace()
        build = cast(Callable[..., dict[str, object]], namespace['build_player_comparison_model'])
        player_one = {'player_id': '1', 'team_name': 'KT', 'name': 'A'}
        player_two = {'player_id': '2', 'team_name': 'LG', 'name': 'B'}
        stat_one = {'avg': 0.333, 'ops': 1.0, 'pa': 4, 'hr': 1, 'rbi': 3}
        stat_two = {'avg': 0.25, 'ops': 0.75, 'pa': 5, 'hr': 0, 'rbi': 1}

        model = build(player_one, stat_one, player_two, stat_two, '만루')

        self.assertIn('만루', cast(str, model['title']))
        fields = cast(list[tuple[str, str]], model['fields'])
        rendered = '\n'.join([name + value for name, value in fields])
        self.assertIn('A', rendered)
        self.assertIn('B', rendered)
        for label in ('AVG', 'OPS', 'PA', 'HR', 'RBI'):
            self.assertIn(label, rendered)


if __name__ == '__main__':
    unittest.main()
