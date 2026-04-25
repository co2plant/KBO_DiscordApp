import asyncio
from typing import Optional

import discord
from discord import app_commands
from discord.ext import tasks

from typing import Literal, Union, NamedTuple
from enum import Enum

import time
from datetime import datetime, timedelta, time as dt_time, timezone
from io import BytesIO

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import database
import kbo_crawler
import settings

TOKEN = settings.DISCORD_TOKEN
CHANNEL_ID = settings.DISCORD_CHANNEL_ID
GUILD_ID = settings.DISCORD_GUILD_ID

MY_GUILD = discord.Object(id=GUILD_ID)  # replace with your guild id

days = ['월', '화', '수', '목', '금', '토', '일']
KST = timezone(timedelta(hours=9))
emoji = [':zero:',':one:',':two:',':three:',':four:',':five:',':six:',':seven:',':eight:',':nine:','🔟']
logo_emoji = {
        '두산':'<:OB:1242717662954651720>',
        'KIA':'<:HT:1242717660958035968>',
        'NC':'<:NC:1242717654423179326>',
        '키움':'<:WO:1242717664397496321>',
        'LG':'<:LG:1242717643966779404>',
        '삼성':'<:SS:1242717658554564608>',
        '롯데':'<:LT:1242717666549039174>',
        'SSG':'<:SK:1242717650505957416>',
        '한화':'<:HH:1242717656214143056>',
        'KT':'<:KT:1242717652447662111>'}

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        # A CommandTree is a special type that holds all the application command
        # state required to make it work. This is a separate class because it
        # allows all the extra state to be opt-in.
        # Whenever you want to work with application commands, your tree is used
        # to store and work with them.
        # Note: When using commands.Bot instead of discord.Client, the bot will
        # maintain its own tree instead.
        self.tree = app_commands.CommandTree(self)

    # In this basic example, we just synchronize the app commands to one guild.
    # Instead of specifying a guild to every command, we copy over our global commands instead.
    # By doing so, we don't have to wait up to an hour until they are shown to the end-user.
    async def setup_hook(self):
        # This copies the global commands over to your guild.
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

intents = discord.Intents.default()
client = MyClient(intents=intents)
_data_ready = False
_data_ready_lock = asyncio.Lock()


def _should_hide_schedule_score(selected_date: datetime, game_time: str, remarks: str, away_score: int, home_score: int) -> bool:
    if remarks not in ('', '-'):
        return False

    if away_score != 0 or home_score != 0:
        return False

    try:
        scheduled_time = datetime.strptime(game_time, '%H:%M').time()
    except ValueError:
        return False

    now = datetime.now()
    if selected_date.date() > now.date():
        return True

    if selected_date.date() < now.date():
        return False

    return now.time() < scheduled_time


def _format_schedule_matchup(selected_date: datetime, row) -> str:
    away_team = row[2]
    home_team = row[3]
    game_time = row[1]
    remarks = row[5]
    away_score = row[7]
    home_score = row[8]

    if away_score == -1:
        away_score = 0
    if home_score == -1:
        home_score = 0

    if _should_hide_schedule_score(selected_date, game_time, remarks, away_score, home_score):
        score_text = 'vs'
    else:
        score_text = f'{away_score} vs {home_score}'

    return f'{away_team:<10} {logo_emoji[away_team]} {score_text} {logo_emoji[home_team]} {home_team:<10}'


async def ensure_data_ready():
    global _data_ready

    if _data_ready:
        return

    async with _data_ready_lock:
        if _data_ready:
            return

        await asyncio.to_thread(database.ensure_schema)

        if not await asyncio.to_thread(database.has_standings_data):
            print('Bootstrapping standings data...')
            await asyncio.to_thread(kbo_crawler.insert_standings)
        else:
            print('Refreshing standings data...')
            await asyncio.to_thread(kbo_crawler.update_standings)

        if not await asyncio.to_thread(database.has_schedule_data):
            print('Bootstrapping schedule data...')
            await asyncio.to_thread(kbo_crawler.insert_schedule_month)

        await asyncio.to_thread(kbo_crawler.refresh_situational_stats_if_stale, datetime.now(KST).year)

        _data_ready = True


def _normalize_team_name(team_name: str) -> str:
    return team_name.strip().upper()


def _find_standings_team(from_db_result, team_name: str):
    normalized_team_name = _normalize_team_name(team_name)

    for team_row in from_db_result:
        if _normalize_team_name(team_row[1]) == normalized_team_name:
            return team_row

    return None


def _is_hot_streak(streak: str) -> bool:
    streak = streak.strip()

    if not streak.endswith('승'):
        return False

    win_count = streak.removesuffix('승')
    return win_count.isdigit() and int(win_count) >= 3


VISIBLE_RUNNER_STATE_SPLIT_KEYS = (
    'bases_empty',
    'runner_on_1',
    'runner_on_2',
    'runner_on_3',
    'runner_on_1_2',
    'runner_on_1_3',
    'runner_on_2_3',
    'bases_loaded',
    'scoring_position',
)

RUNNER_STATE_SPLIT_LABELS = {
    'bases_empty': '주자없음',
    'runner_on_1': '1루',
    'runner_on_2': '2루',
    'runner_on_3': '3루',
    'runner_on_1_2': '1·2루',
    'runner_on_1_3': '1·3루',
    'runner_on_2_3': '2·3루',
    'bases_loaded': '만루',
    'scoring_position': '득점권',
}

RUNNER_STATE_INPUT_ALIASES = {
    '주자없음': 'bases_empty',
    '1루': 'runner_on_1',
    '2루': 'runner_on_2',
    '3루': 'runner_on_3',
    '1,2루': 'runner_on_1_2',
    '1·2루': 'runner_on_1_2',
    '1,3루': 'runner_on_1_3',
    '1·3루': 'runner_on_1_3',
    '2,3루': 'runner_on_2_3',
    '2·3루': 'runner_on_2_3',
    '만루': 'bases_loaded',
    '득점권': 'scoring_position',
}

COUNT_STATE_SPLIT_LABELS = {
    f'count_{balls}_{strikes}': f'{balls}-{strikes}'
    for balls in range(4)
    for strikes in range(3)
}

TEAM_SITUATIONAL_ALIASES = {
    'KT': 'KT WIZ',
    '케이티': 'KT WIZ',
    '두산': 'DOOSAN BEARS',
    'DOOSAN': 'DOOSAN BEARS',
    'KIA': 'KIA TIGERS',
    '기아': 'KIA TIGERS',
    'NC': 'NC DINOS',
    '엔씨': 'NC DINOS',
    '키움': 'KIWOOM HEROES',
    'KIWOOM': 'KIWOOM HEROES',
    'LG': 'LG TWINS',
    '엘지': 'LG TWINS',
    '삼성': 'SAMSUNG LIONS',
    'SAMSUNG': 'SAMSUNG LIONS',
    '롯데': 'LOTTE GIANTS',
    'LOTTE': 'LOTTE GIANTS',
    'SSG': 'SSG LANDERS',
    '에스에스지': 'SSG LANDERS',
    '한화': 'HANWHA EAGLES',
    'HANWHA': 'HANWHA EAGLES',
}


def resolve_runner_state_input(value: str) -> Optional[str]:
    normalized = value.strip()
    if normalized in VISIBLE_RUNNER_STATE_SPLIT_KEYS:
        return normalized
    return RUNNER_STATE_INPUT_ALIASES.get(normalized)


def resolve_count_state_input(value: str) -> Optional[str]:
    normalized = value.strip()
    if normalized in COUNT_STATE_SPLIT_LABELS:
        return normalized
    parts = normalized.split('-')
    if len(parts) != 2:
        return None
    if not all(part.isdigit() for part in parts):
        return None
    balls, strikes = int(parts[0]), int(parts[1])
    split_key = f'count_{balls}_{strikes}'
    return split_key if split_key in COUNT_STATE_SPLIT_LABELS else None


def resolve_situational_team_input(team: str) -> str:
    normalized = _normalize_team_name(team)
    return TEAM_SITUATIONAL_ALIASES.get(normalized, normalized)


def _format_rate(value) -> str:
    if value is None:
        return '-'
    return f'{float(value):.3f}'


def _format_count(value) -> str:
    if value is None:
        return '0'
    return str(value)


def _player_display_name(player_row) -> str:
    if isinstance(player_row, dict):
        return player_row['name']
    return player_row[2]


def _player_team_name(player_row) -> str:
    if isinstance(player_row, dict):
        return player_row['team_name']
    return player_row[1]


def _player_id(player_row) -> str:
    if isinstance(player_row, dict):
        return player_row['player_id']
    return player_row[0]


def _player_role(player_row) -> str:
    if isinstance(player_row, dict):
        position = player_row.get('position')
    elif len(player_row) > 3:
        position = player_row[3]
    else:
        position = None
    return 'pitcher' if str(position or '').strip().lower() == 'pitcher' else 'hitter'


def _player_role_label(player_row) -> str:
    return '투수' if _player_role(player_row) == 'pitcher' else '타자'


def build_player_situational_model(player_row, stat_row, split_label: str):
    return {
        'title': f'{_player_team_name(player_row)} {_player_display_name(player_row)} 상황 성적',
        'fields': [
            ('상황', split_label),
            ('비율', f"AVG {_format_rate(stat_row.get('avg'))} / OBP {_format_rate(stat_row.get('obp'))} / SLG {_format_rate(stat_row.get('slg'))} / OPS {_format_rate(stat_row.get('ops'))}"),
            ('누적', f"PA {_format_count(stat_row.get('pa'))} / AB {_format_count(stat_row.get('ab'))} / H {_format_count(stat_row.get('h'))} / HR {_format_count(stat_row.get('hr'))} / RBI {_format_count(stat_row.get('rbi'))}"),
        ],
    }


def build_pitcher_situational_model(player_row, stat_row, split_label: str):
    return {
        'title': f'{_player_team_name(player_row)} {_player_display_name(player_row)} 투수 상황 성적',
        'fields': [
            ('카운트', split_label),
            ('피안타율', f"OAVG {_format_rate(stat_row.get('avg'))}"),
            ('누적', f"H {_format_count(stat_row.get('h'))} / 2B {_format_count(stat_row.get('double_hits'))} / 3B {_format_count(stat_row.get('triple_hits'))} / HR {_format_count(stat_row.get('hr'))} / BB {_format_count(stat_row.get('bb'))} / HBP {_format_count(stat_row.get('hbp'))} / K {_format_count(stat_row.get('so'))} / WP {_format_count(stat_row.get('wp'))} / BK {_format_count(stat_row.get('bk'))}"),
        ],
    }


def build_team_situational_model(team_name: str, aggregate_row, leader_rows, split_label: str):
    leader_lines = []
    for index, row in enumerate(leader_rows[:3], start=1):
        leader_lines.append(
            f"{index}. {row['name']} OPS {_format_rate(row.get('ops'))} / PA {_format_count(row.get('pa'))} / HR {_format_count(row.get('hr'))} / RBI {_format_count(row.get('rbi'))}"
        )
    return {
        'title': f'{team_name} {split_label} 팀 상황 성적',
        'fields': [
            ('팀 합계', f"AVG {_format_rate(aggregate_row.get('avg'))} / OPS {_format_rate(aggregate_row.get('ops'))} / PA {_format_count(aggregate_row.get('pa'))} / AB {_format_count(aggregate_row.get('ab'))}"),
            ('상위 3명', '\n'.join(leader_lines) if leader_lines else '데이터 없음'),
        ],
    }


def build_player_comparison_model(player_one, stat_one, player_two, stat_two, split_label: str):
    if _player_role(player_one) == 'pitcher' and _player_role(player_two) == 'pitcher':
        return {
            'title': f'{split_label} 투수 비교',
            'fields': [
                (_player_display_name(player_one), f"OAVG {_format_rate(stat_one.get('avg'))} / H {_format_count(stat_one.get('h'))} / HR {_format_count(stat_one.get('hr'))} / BB {_format_count(stat_one.get('bb'))} / K {_format_count(stat_one.get('so'))} / WP {_format_count(stat_one.get('wp'))} / BK {_format_count(stat_one.get('bk'))}"),
                (_player_display_name(player_two), f"OAVG {_format_rate(stat_two.get('avg'))} / H {_format_count(stat_two.get('h'))} / HR {_format_count(stat_two.get('hr'))} / BB {_format_count(stat_two.get('bb'))} / K {_format_count(stat_two.get('so'))} / WP {_format_count(stat_two.get('wp'))} / BK {_format_count(stat_two.get('bk'))}"),
            ],
        }
    return {
        'title': f'{split_label} 선수 비교',
        'fields': [
            (_player_display_name(player_one), f"AVG {_format_rate(stat_one.get('avg'))} / OPS {_format_rate(stat_one.get('ops'))} / PA {_format_count(stat_one.get('pa'))} / HR {_format_count(stat_one.get('hr'))} / RBI {_format_count(stat_one.get('rbi'))}"),
            (_player_display_name(player_two), f"AVG {_format_rate(stat_two.get('avg'))} / OPS {_format_rate(stat_two.get('ops'))} / PA {_format_count(stat_two.get('pa'))} / HR {_format_count(stat_two.get('hr'))} / RBI {_format_count(stat_two.get('rbi'))}"),
        ],
    }


def build_role_mismatch_message(player_one, player_two) -> str:
    return (
        '서로 다른 역할의 선수는 비교할 수 없습니다: '
        f"{_player_display_name(player_one)}({_player_role_label(player_one)}) vs "
        f"{_player_display_name(player_two)}({_player_role_label(player_two)})."
    )


def _model_to_embed(model):
    embed = discord.Embed(title=model['title'], color=0x00AEEF)
    for name, value in model['fields']:
        embed.add_field(name=name, value=value, inline=False)
    embed.set_footer(text='Created').timestamp = datetime.now()
    return embed


def _describe_player_candidates(players):
    return ', '.join(f"{_player_team_name(player)} {_player_display_name(player)}" for player in players)


def _resolve_single_player(name: str):
    players = database.search_players_by_name(name)
    if not players:
        return None, f'{name} 선수를 찾을 수 없습니다.'
    if len(players) > 1:
        return None, f'{name} 선수가 여러 명입니다: {_describe_player_candidates(players)}'
    return players[0], None


async def _send_text(interaction: discord.Interaction, message: str):
    await interaction.followup.send(message, allowed_mentions=discord.AllowedMentions.none())

@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')
    await client.change_presence(status=discord.Status.online, activity=discord.Game('전략 분석'))
    await ensure_data_ready()
    if not update_tables.is_running():
        update_tables.start()

@client.tree.command(name='차렷', description='돌승엽이 잘못한 경우에 사용하십시오.')
async def attention(interaction: discord.Interaction):
    await interaction.response.send_message(f'차렷!')

@client.tree.command(name='열중쉬어', description='돌승엽이 잘했지만 더 잘 해야할 때 사용하십시오.')
async def parade_rest(interaction: discord.Interaction):
    await interaction.response.send_message(f'열중 쉬어!')

@client.tree.command(name='쉬어', description='돌승엽이 잘한 경우에 사용하십시오.')
async def as_you_were(interaction: discord.Interaction):
    await interaction.response.send_message(f'쉬어!')

@tasks.loop(minutes=30)
async def update_tables():
    await asyncio.to_thread(kbo_crawler.update_standings)
    await asyncio.to_thread(kbo_crawler.update_schedule_once, datetime.now(KST).strftime('%m%d'))
    await asyncio.to_thread(kbo_crawler.refresh_situational_stats_if_stale, datetime.now(KST).year)

@update_tables.before_loop
async def before_update_tables():
    await client.wait_until_ready()

@client.tree.command(name='순위', description='돌승엽이 KBO 순위를 당신에게 보여줍니다.')
async def standings(interaction : discord.Interaction):
    await interaction.response.defer(thinking=True)
    await ensure_data_ready()

    embed = discord.Embed(title='KBO 순위', url='https://sports.news.naver.com/kbaseball/record/index?category=kbo', color=0x00AEEF)

    from_db_result = database.select_standings()
    if from_db_result is None:
        await _send_text(interaction, '순위 데이터를 찾을 수 없습니다.')
        return

    lines = ['순위 | 팀 | 승 | 패 | 무 | 승률']
    for index, team_row in enumerate(from_db_result):
        hot_streak = ' 🔥' if _is_hot_streak(team_row[7]) else ''
        lines.append(
            f'{emoji[index+1]} | {logo_emoji[team_row[1]]} {team_row[1]}{hot_streak} | '
            f'{team_row[2]} | {team_row[3]} | {team_row[4]} | {team_row[5]}'
        )

    if lines:
        embed.add_field(name='전체 순위', value='\n'.join(lines), inline=False)

    embed.set_footer(text='Created').timestamp = datetime.now()

    await interaction.followup.send(embed=embed)


@client.tree.command(name='성적', description='선택한 팀의 KBO 상세 성적을 보여줍니다.')
@app_commands.describe(team='상세 성적을 확인할 팀 이름을 입력하세요.')
async def team_standings(interaction: discord.Interaction, team: str):
    await interaction.response.defer(thinking=True)
    await ensure_data_ready()

    from_db_result = database.select_standings()
    if from_db_result is None:
        await _send_text(interaction, '순위 데이터를 찾을 수 없습니다.')
        return

    team_row = _find_standings_team(from_db_result, team)
    if team_row is None:
        await _send_text(interaction, f'{team} 팀의 성적을 찾을 수 없습니다.')
        return

    embed = discord.Embed(
        title=f'{logo_emoji[team_row[1]]} {team_row[1]} 성적',
        url='https://sports.news.naver.com/kbaseball/record/index?category=kbo',
        color=0x00AEEF,
    )
    embed.add_field(
        name='요약',
        value=(
            f'{team_row[0]}위 · {team_row[2]}승 {team_row[3]}패 {team_row[4]}무 ({team_row[5]})'
        ),
        inline=False,
    )
    embed.add_field(name='최근 10경기', value=team_row[6], inline=True)
    embed.add_field(name='연속', value=team_row[7], inline=True)
    embed.add_field(name='홈', value=team_row[8], inline=True)
    embed.add_field(name='원정', value=team_row[9], inline=True)
    embed.set_footer(text='Created').timestamp = datetime.now()

    await interaction.followup.send(embed=embed)


@client.tree.command(name='상황성적', description='선택한 선수의 역할별 상황 성적을 보여줍니다.')
@app_commands.describe(player='상황 성적을 확인할 선수 이름', situation='타자 예: 만루, 득점권 / 투수 예: 0-0, 0-2')
async def player_situational_stats(interaction: discord.Interaction, player: str, situation: str):
    await interaction.response.defer(thinking=True)
    await ensure_data_ready()

    player_row, error_message = _resolve_single_player(player)
    if error_message is not None:
        await _send_text(interaction, error_message)
        return

    player_role = _player_role(player_row)
    if player_role == 'pitcher':
        split_key = resolve_count_state_input(situation)
        if split_key is None:
            await _send_text(interaction, f'{situation} 투수 카운트 상황은 지원하지 않습니다.')
            return
        split_label = COUNT_STATE_SPLIT_LABELS[split_key]
        split_type = 'count_state'
    else:
        split_key = resolve_runner_state_input(situation)
        if split_key is None:
            await _send_text(interaction, f'{situation} 주자 상황은 지원하지 않습니다.')
            return
        split_label = RUNNER_STATE_SPLIT_LABELS[split_key]
        split_type = 'runner_state'

    season = datetime.now(KST).year
    stat_row = database.get_player_situational_stats(_player_id(player_row), season, split_key, split_type=split_type)
    if stat_row is None:
        await _send_text(interaction, f'{player} 선수의 {split_label} 상황 성적을 찾을 수 없습니다.')
        return

    if player_role == 'pitcher':
        model = build_pitcher_situational_model(player_row, stat_row, split_label)
    else:
        model = build_player_situational_model(player_row, stat_row, split_label)
    await interaction.followup.send(embed=_model_to_embed(model))


@client.tree.command(name='팀상황성적', description='선택한 팀의 주자 상황별 타격 성적을 보여줍니다.')
@app_commands.describe(team='상황 성적을 확인할 팀 이름', situation='예: 만루, 득점권, 주자없음')
async def team_situational_stats(interaction: discord.Interaction, team: str, situation: str):
    await interaction.response.defer(thinking=True)
    await ensure_data_ready()

    split_key = resolve_runner_state_input(situation)
    if split_key is None:
        await _send_text(interaction, f'{situation} 상황은 지원하지 않습니다.')
        return

    season = datetime.now(KST).year
    team_key = resolve_situational_team_input(team)
    aggregate_row = database.get_team_situational_aggregate(team_key, season, split_key)
    if aggregate_row is None:
        await _send_text(interaction, f'{team} 팀의 {RUNNER_STATE_SPLIT_LABELS[split_key]} 상황 성적을 찾을 수 없습니다.')
        return

    leader_rows = database.get_team_situational_leaders(team_key, season, split_key)
    model = build_team_situational_model(team_key, aggregate_row, leader_rows, RUNNER_STATE_SPLIT_LABELS[split_key])
    await interaction.followup.send(embed=_model_to_embed(model))


@client.tree.command(name='선수비교', description='두 선수의 같은 역할별 상황 성적을 비교합니다.')
@app_commands.describe(player_one='첫 번째 선수 이름', player_two='두 번째 선수 이름', situation='타자 예: 만루, 득점권 / 투수 예: 0-0, 0-2')
async def compare_player_situational_stats(interaction: discord.Interaction, player_one: str, player_two: str, situation: str):
    await interaction.response.defer(thinking=True)
    await ensure_data_ready()

    first_player, first_error = _resolve_single_player(player_one)
    if first_error is not None:
        await _send_text(interaction, f'선수1: {first_error}')
        return

    second_player, second_error = _resolve_single_player(player_two)
    if second_error is not None:
        await _send_text(interaction, f'선수2: {second_error}')
        return

    first_role = _player_role(first_player)
    second_role = _player_role(second_player)
    if first_role != second_role:
        await _send_text(interaction, build_role_mismatch_message(first_player, second_player))
        return

    if first_role == 'pitcher':
        split_key = resolve_count_state_input(situation)
        if split_key is None:
            await _send_text(interaction, f'{situation} 투수 카운트 상황은 지원하지 않습니다.')
            return
        split_label = COUNT_STATE_SPLIT_LABELS[split_key]
        split_type = 'count_state'
    else:
        split_key = resolve_runner_state_input(situation)
        if split_key is None:
            await _send_text(interaction, f'{situation} 주자 상황은 지원하지 않습니다.')
            return
        split_label = RUNNER_STATE_SPLIT_LABELS[split_key]
        split_type = 'runner_state'

    season = datetime.now(KST).year
    first_stat = database.get_player_situational_stats(_player_id(first_player), season, split_key, split_type=split_type)
    second_stat = database.get_player_situational_stats(_player_id(second_player), season, split_key, split_type=split_type)
    if first_stat is None or second_stat is None:
        await _send_text(interaction, f'{split_label} 상황 비교 데이터를 찾을 수 없습니다.')
        return

    model = build_player_comparison_model(first_player, first_stat, second_player, second_stat, split_label)
    await interaction.followup.send(embed=_model_to_embed(model))

@client.tree.command(name='일정', description='돌승엽이 KBO 경기 일정을 당신에게 보여줍니다.')
@app_commands.describe(args_date='[오늘|내일|모레]를 선택해 언제 일정을 확인할지 선택하세요.')
async def schedule(interaction: discord.Interaction, args_date: Literal['오늘', '내일', '모레']):
    await interaction.response.defer(thinking=True)
    await ensure_data_ready()

    selected_day = {'오늘':0,'내일':1,'모레':2}
    selected_date = (datetime.today()+timedelta(days=selected_day[args_date]))

    embed = discord.Embed(title=f'{selected_date.strftime("%m월 %d일")} {days[selected_date.weekday()]}요일 KBO 경기 일정',url=f'https://m.sports.naver.com/kbaseball/schedule/index?date={selected_date.strftime("%Y-%m-%d")}', color=0x00AEEF)

    from_db_result = database.select_game_and_scord(selected_date.strftime('%m%d'))
    if selected_date.weekday() == 0:
        await _send_text(interaction, '경기가 없는 날입니다.')
        return
    if from_db_result is None:
        await _send_text(interaction, '일정을 찾을 수 없습니다.')
        return

    embed_title= [ f'{"목차":<5}{"시간"}', f'{"경기"}', f'{"구장":<5}{"비고":<5}']
    str = ['', '', '']
    for i in range(len(from_db_result)):
        str[0] = str[0] + f'{emoji[i+1]:<5} {from_db_result[i][1]}\n'
        str[1] = str[1] + _format_schedule_matchup(selected_date, from_db_result[i]) + '\n'
        str[2] = str[2] + f'{from_db_result[i][4]:<5}{from_db_result[i][5]:<5}\n'

    embed.set_footer(text='Created').timestamp = datetime.now()
    embed.add_field(name=embed_title[0], value=str[0], inline=True)
    embed.add_field(name=embed_title[1], value=str[1], inline=True)
    embed.add_field(name=embed_title[2], value=str[2], inline=True)

    await interaction.followup.send(embed=embed)


def main():
    client.run(TOKEN)


if __name__ == '__main__':
    main()
