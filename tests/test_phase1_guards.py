import ast
import unittest
from pathlib import Path



def _read_ast(path: str) -> ast.AST:
    source = Path(path).read_text(encoding='utf-8')
    return ast.parse(source, filename=path)


class TestPhase1Guards(unittest.TestCase):
    def test_update_standings_tuple_shape_and_order(self):
        tree = _read_ast('database.py')

        target_tuple = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id == 'standings_values':
                        if isinstance(node.value, ast.Tuple):
                            target_tuple = node.value

        self.assertIsNotNone(target_tuple, 'standings_values tuple assignment not found')
        self.assertEqual(len(target_tuple.elts), 10, 'standings_values should contain 10 placeholders')

        last = target_tuple.elts[-1]
        self.assertIsInstance(last, ast.Subscript, 'last standings_values value must be game_info[0]')
        self.assertIsInstance(last.value, ast.Name)
        self.assertEqual(last.value.id, 'game_info')

        idx = last.slice.value if isinstance(last.slice, ast.Constant) else None
        self.assertEqual(idx, 0, 'last standings_values value must be game_info[0]')

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
