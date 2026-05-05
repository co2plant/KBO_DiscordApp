import asyncio
import io
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class _FakeResponse:
    def __init__(self):
        self.defer_calls = []

    async def defer(self, *, thinking=False):
        self.defer_calls.append({'thinking': thinking})


class _FakeFollowup:
    def __init__(self):
        self.sent = []

    async def send(self, content=None, embed=None):
        self.sent.append({'content': content, 'embed': embed})


class _FakeInteraction:
    def __init__(self):
        self.response = _FakeResponse()
        self.followup = _FakeFollowup()


class _FakeEmbed:
    def __init__(self, *, title=None, url=None, color=None):
        self.title = title
        self.url = url
        self.color = color
        self.fields = []
        self.footer_text = None
        self.timestamp = None

    def add_field(self, *, name, value, inline):
        self.fields.append({'name': name, 'value': value, 'inline': inline})

    def set_footer(self, *, text):
        self.footer_text = text
        return self


class _FakeObject:
    def __init__(self, *, id):
        self.id = id


class _FakeGame:
    def __init__(self, name):
        self.name = name


class _FakeIntents:
    @staticmethod
    def default():
        return _FakeIntents()


class _FakeClient:
    def __init__(self, *, intents):
        self.intents = intents
        self.user = types.SimpleNamespace(id=1)

    def event(self, function):
        return function

    async def change_presence(self, **_kwargs):
        return None

    async def wait_until_ready(self):
        return None

    def run(self, _token):
        return None


class _FakeCommandTree:
    def __init__(self, _client):
        self.commands = []

    def copy_global_to(self, *, guild):
        self.guild = guild

    async def sync(self, *, guild):
        self.guild = guild

    def command(self, **kwargs):
        def decorator(function):
            self.commands.append((kwargs, function))
            return function

        return decorator


class _FakeLoop:
    def __init__(self, function):
        self.function = function
        self.started = False

    def before_loop(self, function):
        self.before_loop_function = function
        return function

    def is_running(self):
        return self.started

    def start(self):
        self.started = True


class _FakeTasks(types.ModuleType):
    def loop(self, **_kwargs):
        def decorator(function):
            return _FakeLoop(function)

        return decorator


def _describe(**_kwargs):
    def decorator(function):
        return function

    return decorator


class _FakeSettings(types.ModuleType):
    DISCORD_TOKEN = 'token'
    DISCORD_CHANNEL_ID = 123
    DISCORD_GUILD_ID = 456


class _FakeDatabase(types.ModuleType):
    def __init__(self):
        super().__init__('database')
        self.game_rows = []
        self.standings_rows = []
        self.selected_game_keys = []
        self.schedule_checks = []
        self.schedule_exists_by_date = {}

    def ensure_schema(self):
        return None

    def has_standings_data(self):
        return True

    def has_schedule_data(self):
        return True

    def has_schedule_data_for_date(self, selected_date):
        self.schedule_checks.append(selected_date)
        return self.schedule_exists_by_date.get(selected_date, bool(self.game_rows))

    def select_game_and_scord(self, selected_date):
        self.selected_game_keys.append(selected_date)
        return self.game_rows

    def select_standings(self):
        return self.standings_rows


class _FakeCrawler(types.ModuleType):
    def __init__(self):
        super().__init__('kbo_crawler')
        self.schedule_refreshes = []
        self.live_score_refreshes = []
        self.standings_refreshes = 0

    def insert_standings(self):
        return None

    def insert_schedule_month(self):
        return None

    def update_standings(self):
        self.standings_refreshes += 1
        return None

    def update_schedule_once(self, selected_date):
        self.schedule_refreshes.append(selected_date)

    def update_live_scores(self, selected_date):
        self.live_score_refreshes.append(selected_date)


def _fake_discord_modules():
    app_commands = types.ModuleType('discord.app_commands')
    app_commands.CommandTree = _FakeCommandTree
    app_commands.describe = _describe

    discord = types.ModuleType('discord')
    discord.Client = _FakeClient
    discord.Intents = _FakeIntents
    discord.Object = _FakeObject
    discord.Status = types.SimpleNamespace(online='online')
    discord.Game = _FakeGame
    discord.Embed = _FakeEmbed
    discord.Interaction = object
    discord.app_commands = app_commands

    tasks = _FakeTasks('discord.ext.tasks')
    ext = types.ModuleType('discord.ext')
    ext.tasks = tasks

    return {
        'discord': discord,
        'discord.app_commands': app_commands,
        'discord.ext': ext,
        'discord.ext.tasks': tasks,
    }


def _fake_selenium_modules():
    selenium = types.ModuleType('selenium')
    webdriver = types.ModuleType('selenium.webdriver')
    common = types.ModuleType('selenium.webdriver.common')
    by = types.ModuleType('selenium.webdriver.common.by')
    support = types.ModuleType('selenium.webdriver.support')
    expected_conditions = types.ModuleType('selenium.webdriver.support.expected_conditions')
    ui = types.ModuleType('selenium.webdriver.support.ui')

    webdriver.ChromeOptions = object
    webdriver.Chrome = object
    by.By = types.SimpleNamespace(XPATH='xpath')
    ui.WebDriverWait = object

    return {
        'selenium': selenium,
        'selenium.webdriver': webdriver,
        'selenium.webdriver.common': common,
        'selenium.webdriver.common.by': by,
        'selenium.webdriver.support': support,
        'selenium.webdriver.support.expected_conditions': expected_conditions,
        'selenium.webdriver.support.ui': ui,
    }


def _load_kbo_module(database, crawler):
    modules = {}
    modules.update(_fake_discord_modules())
    modules.update(_fake_selenium_modules())
    modules.update(
        {
            'database': database,
            'kbo_crawler': crawler,
            'settings': _FakeSettings('settings'),
        }
    )

    with patch.dict(sys.modules, modules):
        spec = importlib.util.spec_from_file_location('kbo_under_command_flow_test', Path('kbo.py'))
        if spec is None or spec.loader is None:
            raise AssertionError('failed to load kbo.py')

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module._data_ready = True
        return module


class TestScoreTeamCommandFlow(unittest.TestCase):
    def test_scores_uses_cached_today_game_without_schedule_recrawl(self):
        database = _FakeDatabase()
        database.game_rows = [
            ('050400', '18:30', 'LG', '한화', '잠실', '종료', '050400', 3, 2),
        ]
        crawler = _FakeCrawler()
        module = _load_kbo_module(database, crawler)
        interaction = _FakeInteraction()

        with patch('sys.stdout', new=io.StringIO()):
            asyncio.run(module.scores(interaction))

        self.assertEqual(interaction.response.defer_calls, [{'thinking': True}])
        self.assertEqual(crawler.schedule_refreshes, [])
        self.assertEqual(database.schedule_checks, database.selected_game_keys)
        self.assertEqual(len(interaction.followup.sent), 1)

        sent_embed = interaction.followup.sent[0]['embed']
        self.assertIn('KBO 스코어', sent_embed.title)
        self.assertEqual(sent_embed.fields[0]['name'], '오늘 스코어')
        self.assertIn('LG 3 vs 2', sent_embed.fields[0]['value'])
        self.assertIn('한화', sent_embed.fields[0]['value'])

    def test_scores_refreshes_today_game_when_cache_is_missing(self):
        database = _FakeDatabase()
        database.schedule_exists_by_date = {'0505': False}
        crawler = _FakeCrawler()
        module = _load_kbo_module(database, crawler)
        interaction = _FakeInteraction()

        with patch('sys.stdout', new=io.StringIO()):
            asyncio.run(module.scores(interaction))

        self.assertEqual(crawler.schedule_refreshes, ['0505'])
        self.assertEqual(len(interaction.followup.sent), 1)
        self.assertEqual(interaction.followup.sent[0]['content'], '오늘 경기 스코어를 찾을 수 없습니다.')

    def test_scores_refreshes_live_scores_during_game_window(self):
        database = _FakeDatabase()
        database.game_rows = [
            ('050500', '00:00', 'NC', 'LG', '잠실', '-', '050500', 0, 0),
        ]
        crawler = _FakeCrawler()
        module = _load_kbo_module(database, crawler)
        interaction = _FakeInteraction()

        with patch('sys.stdout', new=io.StringIO()):
            asyncio.run(module.scores(interaction))

        self.assertEqual(crawler.schedule_refreshes, [])
        self.assertEqual(crawler.live_score_refreshes, ['0505'])
        self.assertEqual(len(interaction.followup.sent), 1)

    def test_team_summary_uses_cached_today_game_and_refreshes_standings(self):
        database = _FakeDatabase()
        database.standings_rows = [
            ('1', 'LG', 10, 5, 0, '0.667', '7-3', '3승', '5-2', '5-3'),
            ('2', '한화', 9, 6, 0, '0.600', '6-4', '1패', '4-3', '5-3'),
        ]
        database.game_rows = [
            ('050400', '18:30', 'LG', '한화', '잠실', '종료', '050400', 3, 2),
            ('050401', '18:30', 'KIA', '두산', '광주', '종료', '050401', 4, 1),
        ]
        crawler = _FakeCrawler()
        module = _load_kbo_module(database, crawler)
        interaction = _FakeInteraction()

        asyncio.run(module.team_summary(interaction, 'lg'))

        self.assertEqual(interaction.response.defer_calls, [{'thinking': True}])
        self.assertEqual(crawler.schedule_refreshes, [])
        self.assertEqual(crawler.standings_refreshes, 1)
        self.assertEqual(len(interaction.followup.sent), 1)

        sent_embed = interaction.followup.sent[0]['embed']
        field_values = {field['name']: field['value'] for field in sent_embed.fields}
        self.assertIn('LG 팀 요약', sent_embed.title)
        self.assertIn('1위', field_values['성적'])
        self.assertIn('최근 10경기 7-3', field_values['성적'])
        self.assertIn('LG 3 vs 2', field_values['오늘 경기'])
        self.assertNotIn('KIA', field_values['오늘 경기'])

    def test_standings_refreshes_standings_on_command(self):
        database = _FakeDatabase()
        database.standings_rows = [
            ('1', 'LG', 10, 5, 0, '0.667', '7-3', '3승', '5-2', '5-3'),
        ]
        crawler = _FakeCrawler()
        module = _load_kbo_module(database, crawler)
        interaction = _FakeInteraction()

        asyncio.run(module.standings(interaction))

        self.assertEqual(crawler.standings_refreshes, 1)
        self.assertEqual(len(interaction.followup.sent), 1)

    def test_team_standings_refreshes_standings_on_command(self):
        database = _FakeDatabase()
        database.standings_rows = [
            ('1', 'LG', 10, 5, 0, '0.667', '7-3', '3승', '5-2', '5-3'),
        ]
        crawler = _FakeCrawler()
        module = _load_kbo_module(database, crawler)
        interaction = _FakeInteraction()

        asyncio.run(module.team_standings(interaction, 'LG'))

        self.assertEqual(crawler.standings_refreshes, 1)
        self.assertEqual(len(interaction.followup.sent), 1)


if __name__ == '__main__':
    unittest.main()
