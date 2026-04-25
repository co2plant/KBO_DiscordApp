import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class _FakeCursor:
    def __init__(self):
        self.executed = []
        self._last_query = ''

    def execute(self, query, params=None):
        self.executed.append((query, params))
        self._last_query = query

    def fetchone(self):
        if 'INFORMATION_SCHEMA.COLUMNS' in self._last_query:
            return (1,)
        return None

    def fetchall(self):
        if 'SHOW INDEX FROM Standings' in self._last_query:
            return [(None, None, None, None, 'team')]
        if 'FROM `Standings`' in self._last_query:
            return [('1', 'LG', 16, 7, 0, '0.696', '7승0무3패', '2승', '9-0-5', '7-0-2')]
        if 'FROM `Games`' in self._last_query:
            return [('042500', '18:30', '두산', 'LG', '잠실', '종료')]
        if 'FROM `Scores`' in self._last_query:
            return [('042500', 1, 3)]
        if 'FROM `players`' in self._last_query:
            return []
        if 'FROM `situational_stats`' in self._last_query:
            return []
        return []

    def close(self):
        return None


class _FakeConnection:
    def __init__(self):
        self.cursor_instance = _FakeCursor()
        self.commit_calls = 0
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commit_calls += 1

    def close(self):
        self.closed = True


class _SettingsModule(types.ModuleType):
    DB_HOST: str
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str


class _PymysqlModule(types.ModuleType):
    connect: object


def _load_database_module(connection):
    fake_settings = _SettingsModule('settings')
    fake_settings.DB_HOST = 'db'
    fake_settings.DB_USER = 'user'
    fake_settings.DB_PASSWORD = 'password'
    fake_settings.DB_NAME = 'kbo'

    fake_pymysql = _PymysqlModule('pymysql')
    fake_pymysql.connect = lambda **_kwargs: connection

    with patch.dict(sys.modules, {'settings': fake_settings, 'pymysql': fake_pymysql}):
        spec = importlib.util.spec_from_file_location('database_under_test', Path('database.py'))
        if spec is None or spec.loader is None:
            raise AssertionError('failed to load database.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


class TestSqlDumpExport(unittest.TestCase):
    def test_export_sql_snapshot_writes_restoreable_dump(self):
        conn = _FakeConnection()
        database = _load_database_module(conn)

        with tempfile.TemporaryDirectory() as temp_dir:
            dump_path = database.export_sql_snapshot(temp_dir, filename='snapshot.sql')
            contents = Path(dump_path).read_text(encoding='utf-8')

        self.assertIn('SET FOREIGN_KEY_CHECKS=0;', contents)
        self.assertIn('DELETE FROM `Scores`;', contents)
        self.assertIn('INSERT INTO `Standings`', contents)
        self.assertIn("'LG'", contents)
        self.assertIn('INSERT INTO `Games`', contents)
        self.assertIn('SET FOREIGN_KEY_CHECKS=1;', contents)
        self.assertTrue(conn.closed)


if __name__ == '__main__':
    unittest.main()
