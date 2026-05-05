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
_LIVE_SCORE_REFRESH_LEAD_MINUTES = 10
_FINAL_GAME_REMARKS = ('경기종료', '종료', '취소')


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


def _format_score_line(selected_date: datetime, row) -> str:
    away_team = row[2]
    home_team = row[3]
    game_time = row[1]
    stadium = row[4]
    remarks = row[5]
    away_score = row[7]
    home_score = row[8]

    if away_score in (None, -1, '-1', ''):
        away_score = 0
    if home_score in (None, -1, '-1', ''):
        home_score = 0

    if _should_hide_schedule_score(selected_date, game_time, remarks, away_score, home_score):
        score_text = 'vs'
        status_text = '경기 전'
    else:
        score_text = f'{away_score} vs {home_score}'
        status_text = remarks if remarks not in ('', '-') else '진행/종료'

    away_logo = logo_emoji.get(away_team, '')
    home_logo = logo_emoji.get(home_team, '')

    return f'{game_time} | {away_logo} {away_team} {score_text} {home_logo} {home_team} | {stadium} | {status_text}'


def _find_team_games(games, team_name: str):
    normalized_team_name = _normalize_team_name(team_name)

    return [
        game_row
        for game_row in games
        if _normalize_team_name(game_row[2]) == normalized_team_name
        or _normalize_team_name(game_row[3]) == normalized_team_name
    ]


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

        today_key = datetime.now(KST).strftime('%m%d')
        if not await asyncio.to_thread(database.has_schedule_data_for_date, today_key):
            print(f'Bootstrapping schedule data for {today_key}...')
            await asyncio.to_thread(kbo_crawler.update_schedule_once, today_key)

        _data_ready = True


async def _refresh_standings_for_command():
    try:
        await asyncio.to_thread(kbo_crawler.update_standings)
    except Exception as exc:
        print(f'Failed to refresh standings: {exc}')


async def _ensure_schedule_data_for_date(selected_date_key: str):
    if await asyncio.to_thread(database.has_schedule_data_for_date, selected_date_key):
        return

    try:
        await asyncio.to_thread(kbo_crawler.update_schedule_once, selected_date_key)
    except Exception as exc:
        print(f'Failed to refresh schedule for {selected_date_key}: {exc}')


def _is_final_game_status(remarks: str) -> bool:
    remarks = str(remarks or '')
    return any(final_status in remarks for final_status in _FINAL_GAME_REMARKS)


def _should_refresh_live_scores(selected_date: datetime, game_rows, now: Optional[datetime] = None) -> bool:
    if not game_rows:
        return False

    now = datetime.now(KST) if now is None else now
    if selected_date.date() != now.date():
        return False

    for row in game_rows:
        game_time = row[1]
        remarks = row[5]
        if _is_final_game_status(remarks):
            continue

        try:
            scheduled_time = datetime.strptime(game_time, '%H:%M').time()
        except ValueError:
            continue

        scheduled_datetime = selected_date.replace(
            hour=scheduled_time.hour,
            minute=scheduled_time.minute,
            second=0,
            microsecond=0,
        )
        if now >= scheduled_datetime - timedelta(minutes=_LIVE_SCORE_REFRESH_LEAD_MINUTES):
            return True

    return False


async def _refresh_live_scores_for_command(selected_date_key: str, selected_date: datetime):
    game_rows = await asyncio.to_thread(database.select_game_and_scord, selected_date_key)
    if not _should_refresh_live_scores(selected_date, game_rows):
        return game_rows

    try:
        refreshed_count = await asyncio.to_thread(kbo_crawler.update_live_scores, selected_date_key)
        print(f'Refreshed live scores for {selected_date_key}: {refreshed_count}')
    except Exception as exc:
        print(f'Failed to refresh live scores for {selected_date_key}: {exc}')
        return game_rows

    return await asyncio.to_thread(database.select_game_and_scord, selected_date_key)


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

@tasks.loop(time=dt_time(hour=6, tzinfo=KST))
async def update_tables():
    await asyncio.to_thread(kbo_crawler.update_standings)
    await asyncio.to_thread(kbo_crawler.update_schedule_once, datetime.now(KST).strftime('%m%d'))

@update_tables.before_loop
async def before_update_tables():
    await client.wait_until_ready()

@client.tree.command(name='순위', description='돌승엽이 KBO 순위를 당신에게 보여줍니다.')
async def standings(interaction : discord.Interaction):
    await interaction.response.defer(thinking=True)
    await ensure_data_ready()
    await _refresh_standings_for_command()

    embed = discord.Embed(title='KBO 순위', url='https://sports.news.naver.com/kbaseball/record/index?category=kbo', color=0x00AEEF)

    from_db_result = database.select_standings()
    if from_db_result is None:
        await interaction.followup.send('순위 데이터를 찾을 수 없습니다.')
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
    await _refresh_standings_for_command()

    from_db_result = database.select_standings()
    if from_db_result is None:
        await interaction.followup.send('순위 데이터를 찾을 수 없습니다.')
        return

    team_row = _find_standings_team(from_db_result, team)
    if team_row is None:
        await interaction.followup.send(f'{team} 팀의 성적을 찾을 수 없습니다.')
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

@client.tree.command(name='일정', description='돌승엽이 KBO 경기 일정을 당신에게 보여줍니다.')
@app_commands.describe(args_date='[오늘|내일|모레]를 선택해 언제 일정을 확인할지 선택하세요.')
async def schedule(interaction: discord.Interaction, args_date: Literal['오늘', '내일', '모레']):
    await interaction.response.defer(thinking=True)
    await ensure_data_ready()

    selected_day = {'오늘':0,'내일':1,'모레':2}
    selected_date = (datetime.today()+timedelta(days=selected_day[args_date]))
    selected_date_key = selected_date.strftime('%m%d')
    await _ensure_schedule_data_for_date(selected_date_key)

    embed = discord.Embed(title=f'{selected_date.strftime("%m월 %d일")} {days[selected_date.weekday()]}요일 KBO 경기 일정',url=f'https://m.sports.naver.com/kbaseball/schedule/index?date={selected_date.strftime("%Y-%m-%d")}', color=0x00AEEF)

    from_db_result = database.select_game_and_scord(selected_date_key)
    if selected_date.weekday() == 0:
        await interaction.followup.send('경기가 없는 날입니다.')
        return
    if from_db_result is None:
        await interaction.followup.send('일정을 찾을 수 없습니다.')
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


@client.tree.command(name='스코어', description='오늘 KBO 경기 스코어를 보여줍니다.')
async def scores(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    await ensure_data_ready()

    selected_date = datetime.now(KST)
    selected_date_key = selected_date.strftime('%m%d')

    await _ensure_schedule_data_for_date(selected_date_key)

    from_db_result = await _refresh_live_scores_for_command(selected_date_key, selected_date)
    if from_db_result is None or len(from_db_result) == 0:
        await interaction.followup.send('오늘 경기 스코어를 찾을 수 없습니다.')
        return

    embed = discord.Embed(
        title=f'{selected_date.strftime("%m월 %d일")} KBO 스코어',
        url=f'https://m.sports.naver.com/kbaseball/schedule/index?date={selected_date.strftime("%Y-%m-%d")}',
        color=0x00AEEF,
    )
    embed.add_field(
        name='오늘 스코어',
        value='\n'.join(_format_score_line(selected_date, row) for row in from_db_result),
        inline=False,
    )
    embed.set_footer(text='Created').timestamp = datetime.now()

    await interaction.followup.send(embed=embed)


@client.tree.command(name='팀', description='선택한 팀의 오늘 경기와 성적 요약을 보여줍니다.')
@app_commands.describe(team='요약을 확인할 팀 이름을 입력하세요.')
async def team_summary(interaction: discord.Interaction, team: str):
    await interaction.response.defer(thinking=True)
    await ensure_data_ready()

    selected_date = datetime.now(KST)
    selected_date_key = selected_date.strftime('%m%d')

    await _ensure_schedule_data_for_date(selected_date_key)
    game_rows = await _refresh_live_scores_for_command(selected_date_key, selected_date)
    await _refresh_standings_for_command()

    standings_rows = database.select_standings()
    team_row = _find_standings_team(standings_rows, team) if standings_rows is not None else None

    team_games = _find_team_games(game_rows or [], team)

    if team_row is None and not team_games:
        await interaction.followup.send(f'{team} 팀 정보를 찾을 수 없습니다.')
        return

    team_name = team_row[1] if team_row is not None else team
    if team_row is None:
        first_game = team_games[0]
        if _normalize_team_name(first_game[2]) == _normalize_team_name(team):
            team_name = first_game[2]
        else:
            team_name = first_game[3]

    team_logo = logo_emoji.get(team_name, '')
    embed = discord.Embed(
        title=f'{team_logo} {team_name} 팀 요약',
        url='https://sports.news.naver.com/kbaseball/record/index?category=kbo',
        color=0x00AEEF,
    )

    if team_row is not None:
        embed.add_field(
            name='성적',
            value=(
                f'{team_row[0]}위 · {team_row[2]}승 {team_row[3]}패 {team_row[4]}무 ({team_row[5]})\n'
                f'최근 10경기 {team_row[6]} · 연속 {team_row[7]}\n'
                f'홈 {team_row[8]} · 원정 {team_row[9]}'
            ),
            inline=False,
        )
    else:
        embed.add_field(name='성적', value='순위 데이터를 찾을 수 없습니다.', inline=False)

    if team_games:
        embed.add_field(
            name='오늘 경기',
            value='\n'.join(_format_score_line(selected_date, row) for row in team_games),
            inline=False,
        )
    else:
        embed.add_field(name='오늘 경기', value='오늘 예정된 경기가 없습니다.', inline=False)

    embed.set_footer(text='Created').timestamp = datetime.now()

    await interaction.followup.send(embed=embed)


def main():
    client.run(TOKEN)


if __name__ == '__main__':
    main()
