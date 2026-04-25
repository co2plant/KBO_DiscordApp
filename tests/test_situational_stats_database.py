from datetime import datetime, timedelta, timezone
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
        self.fetchall_result: list[object] = []

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


class TestSituationalStatsDatabase(unittest.TestCase):
    def test_ensure_schema_creates_players_and_situational_stats_tables(self):
        schema_conn = _FakeConnection()
        database = _load_database_module([schema_conn])

        database.ensure_schema()

        executed_sql = '\n'.join(query for query, _ in schema_conn.cursor_instance.executed)
        self.assertIn('CREATE TABLE IF NOT EXISTS players', executed_sql)
        self.assertIn('player_id VARCHAR(32) PRIMARY KEY', executed_sql)
        self.assertIn('CREATE TABLE IF NOT EXISTS situational_stats', executed_sql)
        self.assertIn('wp INT', executed_sql)
        self.assertIn('bk INT', executed_sql)
        self.assertIn('UNIQUE KEY uq_situational_stats', executed_sql)
        self.assertIn('season, entity_type, entity_id, split_type, split_key', executed_sql)
        self.assertEqual(schema_conn.commit_calls, 1)
        self.assertTrue(schema_conn.closed)

    def test_upsert_player_updates_existing_player(self):
        schema_conn = _FakeConnection()
        upsert_conn = _FakeConnection()
        database = _load_database_module([schema_conn, upsert_conn])

        database.ensure_schema()
        database.upsert_player({
            'player_id': '67341',
            'team_name': '키움',
            'name': 'LEE Jung Hoo',
            'position': 'Outfielder',
            'born': '20/08/1998',
            'height_weight': '185cm/86kg',
            'salary': '1100000000',
            'debut': '17',
            'updated_at': '2026-04-24 00:00:00',
        })

        executed = upsert_conn.cursor_instance.executed
        self.assertEqual(len(executed), 1)
        self.assertIn('INSERT INTO players', executed[0][0])
        self.assertIn('ON DUPLICATE KEY UPDATE', executed[0][0])
        self.assertEqual(executed[0][1][0], '67341')
        self.assertEqual(upsert_conn.commit_calls, 1)
        self.assertTrue(upsert_conn.closed)

    def test_upsert_situational_stat_updates_unique_split_row(self):
        schema_conn = _FakeConnection()
        upsert_conn = _FakeConnection()
        database = _load_database_module([schema_conn, upsert_conn])

        database.ensure_schema()
        database.upsert_situational_stat({
            'season': 2026,
            'entity_type': 'player',
            'entity_id': '67341',
            'team_name': '키움',
            'split_type': 'runner_state',
            'split_key': 'bases_loaded',
            'pa': 4,
            'ab': 3,
            'h': 1,
            'double_hits': 0,
            'triple_hits': 0,
            'hr': 1,
            'rbi': 4,
            'bb': 1,
            'hbp': 0,
            'so': 1,
            'gidp': 0,
            'wp': 0,
            'bk': 0,
            'avg': 0.333,
            'obp': 0.5,
            'slg': 1.333,
            'ops': 1.833,
            'source_updated_at': '2026-04-24 00:00:00',
        })

        executed = upsert_conn.cursor_instance.executed
        self.assertEqual(len(executed), 1)
        self.assertIn('INSERT INTO situational_stats', executed[0][0])
        self.assertIn('ON DUPLICATE KEY UPDATE', executed[0][0])
        self.assertEqual(executed[0][1][:6], (2026, 'player', '67341', '키움', 'runner_state', 'bases_loaded'))
        self.assertEqual(upsert_conn.commit_calls, 1)
        self.assertTrue(upsert_conn.closed)

    def test_upsert_pitcher_count_stat_persists_wp_and_bk(self):
        schema_conn = _FakeConnection()
        upsert_conn = _FakeConnection()
        database = _load_database_module([schema_conn, upsert_conn])

        database.ensure_schema()
        database.upsert_situational_stat({
            'season': 2026,
            'entity_type': 'player',
            'entity_id': '77637',
            'team_name': 'KIA TIGERS',
            'split_type': 'count_state',
            'split_key': 'count_0_2',
            'h': 1,
            'double_hits': 0,
            'triple_hits': 0,
            'hr': 0,
            'bb': 1,
            'hbp': 0,
            'so': 5,
            'wp': 0,
            'bk': 0,
            'avg': 0.083,
            'source_updated_at': '2026-04-24 00:00:00',
        })

        executed = upsert_conn.cursor_instance.executed
        self.assertIn('wp, bk', executed[0][0])
        self.assertIn('wp = VALUES(wp)', executed[0][0])
        self.assertIn('bk = VALUES(bk)', executed[0][0])
        self.assertEqual(executed[0][1][5], 'count_0_2')

    def test_search_players_by_name_exact_normalized_and_ambiguous(self):
        schema_conn = _FakeConnection()
        search_conn = _FakeConnection()
        search_conn.cursor_instance.fetchall_result = [
            ('67341', '키움', 'LEE Jung Hoo', 'Outfielder', '20/08/1998', '185cm/86kg', '1100000000', '17', '2026-04-24'),
        ]
        database = _load_database_module([schema_conn, search_conn])

        database.ensure_schema()
        rows = database.search_players_by_name('LEE Jung Hoo')

        self.assertEqual(rows[0]['player_id'], '67341')
        self.assertEqual(rows[0]['team_name'], '키움')
        self.assertIn("REPLACE(LOWER(name), ' ', '')", search_conn.cursor_instance.executed[0][0])
        self.assertEqual(search_conn.cursor_instance.executed[0][1][1], 'leejunghoo')

    def test_get_player_situational_stats_by_split(self):
        schema_conn = _FakeConnection()
        select_conn = _FakeConnection()
        select_conn.cursor_instance.fetchone_result = (
            2026, 'player', '67341', '키움', 'runner_state', 'bases_loaded', 4, 3, 1, 0, 0, 1,
            4, 1, 0, 1, 0, 0, 0, 0.333, 0.5, 1.333, 1.833, '2026-04-24',
        )
        database = _load_database_module([schema_conn, select_conn])

        database.ensure_schema()
        row = database.get_player_situational_stats('67341', 2026, 'bases_loaded')

        self.assertEqual(row['entity_id'], '67341')
        self.assertEqual(row['split_key'], 'bases_loaded')
        self.assertEqual(select_conn.cursor_instance.executed[0][1], ('67341', 2026, 'runner_state', 'bases_loaded'))

    def test_get_pitcher_count_situational_stats_by_split(self):
        schema_conn = _FakeConnection()
        select_conn = _FakeConnection()
        select_conn.cursor_instance.fetchone_result = (
            2026, 'player', '77637', 'KIA TIGERS', 'count_state', 'count_0_2', None, None, 1, 0, 0, 0,
            None, 1, 0, 5, None, 0, 0, 0.083, None, None, None, '2026-04-24',
        )
        database = _load_database_module([schema_conn, select_conn])

        database.ensure_schema()
        row = database.get_player_situational_stats('77637', 2026, 'count_0_2', split_type='count_state')

        self.assertEqual(row['entity_id'], '77637')
        self.assertEqual(row['split_type'], 'count_state')
        self.assertEqual(row['wp'], 0)
        self.assertEqual(row['bk'], 0)
        self.assertEqual(select_conn.cursor_instance.executed[0][1], ('77637', 2026, 'count_state', 'count_0_2'))

    def test_get_team_situational_aggregate_from_player_rows(self):
        schema_conn = _FakeConnection()
        aggregate_conn = _FakeConnection()
        aggregate_conn.cursor_instance.fetchone_result = (3, 10, 8, 4, 1, 0, 1, 5, 2, 0, 2, 1)
        database = _load_database_module([schema_conn, aggregate_conn])

        database.ensure_schema()
        row = database.get_team_situational_aggregate('KT', 2026, 'bases_loaded')

        self.assertEqual(row['pa'], 10)
        self.assertEqual(row['ab'], 8)
        self.assertEqual(row['avg'], 0.5)
        self.assertEqual(row['ops'], 1.6)
        self.assertIn("entity_type = 'player'", aggregate_conn.cursor_instance.executed[0][0])

    def test_get_team_situational_aggregate_returns_none_without_player_rows(self):
        schema_conn = _FakeConnection()
        aggregate_conn = _FakeConnection()
        aggregate_conn.cursor_instance.fetchone_result = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        database = _load_database_module([schema_conn, aggregate_conn])

        database.ensure_schema()
        row = database.get_team_situational_aggregate('KT', 2026, 'bases_loaded')

        self.assertIsNone(row)

    def test_get_team_situational_leaders_returns_top_three(self):
        schema_conn = _FakeConnection()
        leader_conn = _FakeConnection()
        leader_conn.cursor_instance.fetchall_result = [
            ('1', 'A', 'KT', 5, 4, 2, 1, 3, 0.5, 1.5),
            ('2', 'B', 'KT', 4, 4, 1, 0, 1, 0.25, 0.75),
        ]
        database = _load_database_module([schema_conn, leader_conn])

        database.ensure_schema()
        rows = database.get_team_situational_leaders('KT', 2026, 'bases_loaded')

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['name'], 'A')
        self.assertIn('ORDER BY s.ops DESC, s.pa DESC, p.name', leader_conn.cursor_instance.executed[0][0])
        self.assertEqual(leader_conn.cursor_instance.executed[0][1], ('KT', 2026, 'bases_loaded', 3))

    def test_situational_refresh_freshness_helper(self):
        kst = timezone(timedelta(hours=9))
        now = datetime(2026, 4, 24, 12, 0, tzinfo=kst)

        schema_conn = _FakeConnection()
        fresh_conn = _FakeConnection()
        fresh_conn.cursor_instance.fetchone_result = (datetime(2026, 4, 24, 6, 0, tzinfo=kst),)
        database = _load_database_module([schema_conn, fresh_conn])

        database.ensure_schema()
        self.assertFalse(database.should_refresh_situational_stats(now))

        schema_conn = _FakeConnection()
        stale_conn = _FakeConnection()
        stale_conn.cursor_instance.fetchone_result = (datetime(2026, 4, 23, 23, 0, tzinfo=kst),)
        database = _load_database_module([schema_conn, stale_conn])

        database.ensure_schema()
        self.assertTrue(database.should_refresh_situational_stats(now))

    def test_has_situational_stats_checks_split_type(self):
        schema_conn = _FakeConnection()
        count_conn = _FakeConnection()
        count_conn.cursor_instance.fetchone_result = (1,)
        database = _load_database_module([schema_conn, count_conn])

        database.ensure_schema()
        self.assertTrue(database.has_situational_stats('count_state'))

        self.assertIn("split_type = %s", count_conn.cursor_instance.executed[0][0])
        self.assertEqual(count_conn.cursor_instance.executed[0][1], ('count_state',))


if __name__ == '__main__':
    unittest.main()
