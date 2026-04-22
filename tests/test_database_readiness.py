import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class _FakeCursor:
    def __init__(self):
        self.executed = []
        self.fetchone_result: object | None = None
        self.fetchall_result = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchone(self):
        return self.fetchone_result

    def fetchall(self):
        return self.fetchall_result

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


def _load_database_module(connections):
    fake_settings = _SettingsModule('settings')
    fake_settings.DB_HOST = 'db'
    fake_settings.DB_USER = 'user'
    fake_settings.DB_PASSWORD = 'password'
    fake_settings.DB_NAME = 'kbo'

    fake_pymysql = _PymysqlModule('pymysql')

    connection_queue = list(connections)

    def connect(**_kwargs):
        return connection_queue.pop(0)

    fake_pymysql.connect = connect

    with patch.dict(sys.modules, {'settings': fake_settings, 'pymysql': fake_pymysql}):
        spec = importlib.util.spec_from_file_location('database_under_test', Path('database.py'))
        if spec is None or spec.loader is None:
            raise AssertionError('failed to load database.py')

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


class TestDatabaseReadiness(unittest.TestCase):
    def test_ensure_schema_creates_required_tables(self):
        schema_conn = _FakeConnection()
        database = _load_database_module([schema_conn])

        database.ensure_schema()

        executed_sql = '\n'.join(query for query, _ in schema_conn.cursor_instance.executed)
        self.assertIn('CREATE TABLE IF NOT EXISTS Standings', executed_sql)
        self.assertIn('CREATE TABLE IF NOT EXISTS Games', executed_sql)
        self.assertIn('CREATE TABLE IF NOT EXISTS Scores', executed_sql)
        self.assertEqual(schema_conn.commit_calls, 1)
        self.assertTrue(schema_conn.closed)

    def test_update_game_and_score_upserts_game_and_score_rows(self):
        schema_conn = _FakeConnection()
        update_conn = _FakeConnection()
        database = _load_database_module([schema_conn, update_conn])

        database.ensure_schema()
        database.update_game_and_score(['042200', '18:30', '두산', '3', '2', 'LG', '잠실', '정상 진행'])

        executed = update_conn.cursor_instance.executed
        self.assertEqual(len(executed), 2)

        self.assertIn('INSERT INTO Games', executed[0][0])
        self.assertIn('ON DUPLICATE KEY UPDATE', executed[0][0])
        self.assertEqual(executed[0][1], ('042200', '18:30', '두산', 'LG', '잠실', '정상 진행'))

        self.assertIn('INSERT INTO Scores', executed[1][0])
        self.assertIn('ON DUPLICATE KEY UPDATE', executed[1][0])
        self.assertEqual(executed[1][1], ('042200', '3', '2'))
        self.assertEqual(update_conn.commit_calls, 1)
        self.assertTrue(update_conn.closed)

    def test_has_standings_data_requires_all_teams(self):
        schema_conn = _FakeConnection()
        count_conn = _FakeConnection()
        count_conn.cursor_instance.fetchone_result = (8,)
        database = _load_database_module([schema_conn, count_conn])

        database.ensure_schema()
        self.assertFalse(database.has_standings_data())

        schema_conn = _FakeConnection()
        count_conn = _FakeConnection()
        count_conn.cursor_instance.fetchone_result = (10,)
        database = _load_database_module([schema_conn, count_conn])

        database.ensure_schema()
        self.assertTrue(database.has_standings_data())


if __name__ == '__main__':
    unittest.main()
