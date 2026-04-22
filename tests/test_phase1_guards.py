import ast
import unittest
from pathlib import Path



def _read_ast(path: str) -> ast.Module:
    source = Path(path).read_text(encoding='utf-8')
    return ast.parse(source, filename=path)


def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f'{name} function not found')


def _find_named_tuple_assignment(function_node: ast.FunctionDef, target_name: str) -> ast.Tuple:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Tuple):
            continue

        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == target_name:
                return node.value

    raise AssertionError(f'{target_name} tuple assignment not found in {function_node.name}')


def _assert_game_info_index(test_case: unittest.TestCase, element: ast.AST, expected_index: int, message: str):
    test_case.assertIsInstance(element, ast.Subscript, message)
    if not isinstance(element, ast.Subscript):
        raise AssertionError(message)

    test_case.assertIsInstance(element.value, ast.Name, message)
    if not isinstance(element.value, ast.Name):
        raise AssertionError(message)

    test_case.assertEqual(element.value.id, 'game_info', message)

    idx = element.slice.value if isinstance(element.slice, ast.Constant) else None
    test_case.assertEqual(idx, expected_index, message)


def _find_database_update_standings_call(function_node: ast.FunctionDef) -> ast.Call:
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name):
            continue
        if node.func.value.id == 'database' and node.func.attr == 'update_standings':
            return node

    raise AssertionError('database.update_standings(...) call not found')


class TestPhase1Guards(unittest.TestCase):
    def test_insert_standings_tuple_shape_and_order(self):
        tree = _read_ast('database.py')
        insert_standings = _find_function(tree, 'insert_standings')
        target_tuple = _find_named_tuple_assignment(insert_standings, 'standings_values')

        self.assertEqual(len(target_tuple.elts), 10, 'standings_values should contain 10 placeholders')

        _assert_game_info_index(self, target_tuple.elts[0], 0, 'first insert standings_values value must be game_info[0]')
        _assert_game_info_index(self, target_tuple.elts[-1], 9, 'last insert standings_values value must be game_info[9]')

    def test_update_standings_tuple_shape_and_order(self):
        tree = _read_ast('database.py')
        update_standings = _find_function(tree, 'update_standings')
        target_tuple = _find_named_tuple_assignment(update_standings, 'standings_values')

        self.assertEqual(len(target_tuple.elts), 10, 'standings_values should contain 10 placeholders')

        _assert_game_info_index(self, target_tuple.elts[0], 1, 'first update standings_values value must be game_info[1]')
        _assert_game_info_index(self, target_tuple.elts[-1], 0, 'last update standings_values value must be game_info[0]')

    def test_crawler_update_standings_passes_id_first(self):
        tree = _read_ast('kbo_crawler.py')
        update_standings = _find_function(tree, 'update_standings')
        update_call = _find_database_update_standings_call(update_standings)

        self.assertEqual(len(update_call.args), 1, 'database.update_standings should receive one list argument')
        self.assertIsInstance(update_call.args[0], ast.List, 'database.update_standings argument must be a list literal')
        if not isinstance(update_call.args[0], ast.List):
            raise AssertionError('database.update_standings argument must be a list literal')

        arg_names = [elt.id if isinstance(elt, ast.Name) else None for elt in update_call.args[0].elts]
        self.assertEqual(
            arg_names,
            ['id', 'team', 'win', 'lose', 'draw', 'rate', 'last_10', 'streak', 'home', 'away'],
            'crawler must pass update_standings values with id first',
        )

    def test_crawler_import_guard_exists(self):
        tree = _read_ast('kbo_crawler.py')

        guarded_call_found = False

        for node in tree.body:
            if not isinstance(node, ast.If):
                continue

            is_name_main_check = (
                isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name)
                and node.test.left.id == '__name__'
                and len(node.test.ops) == 1
                and isinstance(node.test.ops[0], ast.Eq)
                and len(node.test.comparators) == 1
                and isinstance(node.test.comparators[0], ast.Constant)
                and node.test.comparators[0].value == '__main__'
            )

            if not is_name_main_check:
                continue

            for child in node.body:
                if isinstance(child, ast.Expr) and isinstance(child.value, ast.Call):
                    fn = child.value.func
                    if isinstance(fn, ast.Name) and fn.id == 'insert_schedule_month':
                        guarded_call_found = True

        self.assertTrue(guarded_call_found, 'insert_schedule_month() must be guarded by __name__ check')


if __name__ == '__main__':
    unittest.main()
