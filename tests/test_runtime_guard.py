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


class TestRuntimeGuard(unittest.TestCase):
    def test_main_calls_client_run_with_token(self):
        tree = _read_ast('kbo.py')
        main_function = _find_function(tree, 'main')

        run_call_found = False
        for node in ast.walk(main_function):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            if not isinstance(node.func.value, ast.Name):
                continue
            if node.func.value.id != 'client' or node.func.attr != 'run':
                continue
            if len(node.args) != 1:
                continue
            if isinstance(node.args[0], ast.Name) and node.args[0].id == 'TOKEN':
                run_call_found = True

        self.assertTrue(run_call_found, 'main() must call client.run(TOKEN)')

    def test_client_run_is_guarded_by_main_check(self):
        tree = _read_ast('kbo.py')

        guarded_main_found = False
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
                if not isinstance(child, ast.Expr) or not isinstance(child.value, ast.Call):
                    continue
                if isinstance(child.value.func, ast.Name) and child.value.func.id == 'main':
                    guarded_main_found = True

        self.assertTrue(guarded_main_found, 'main() must be guarded by __name__ check')


if __name__ == '__main__':
    unittest.main()
