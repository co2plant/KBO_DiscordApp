import json
from typing import Optional

import discord
from discord import app_commands

from typing import Literal, Union, NamedTuple
from enum import Enum

import time
from datetime import datetime, timedelta
from io import BytesIO

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import database

with open('config.json') as f:
    data = json.load(f)
    TOKEN = data['DISCORD']['TOKEN']
    CHANNEL_ID = data['DISCORD']['CHANNEL_ID']
    GUILD_ID = data['DISCORD']['GUILD_ID']

MY_GUILD = discord.Object(id=GUILD_ID)  # replace with your guild id

days = ['월', '화', '수', '목', '금', '토', '일']
emoji = [':zero:',':one:',':two:',':three:',':four:',':five:',':six:',':seven:',':eight:',':nine:']
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

@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')
    await client.change_presence(status=discord.Status.online, activity=discord.Game('전략 분석'))

@client.tree.command(name='차렷', description='돌승엽이 잘못한 경우에 사용하십시오.')
async def attention(interaction: discord.Interaction):
    await interaction.response.send_message(f'차렷!')

@client.tree.command(name='열중쉬어', description='돌승엽이 잘했지만 더 잘 해야할 때 사용하십시오.')
async def parade_rest(interaction: discord.Interaction):
    await interaction.response.send_message(f'열중 쉬어!')

@client.tree.command(name='쉬어', description='돌승엽이 잘한 경우에 사용하십시오.')
async def as_you_were(interaction: discord.Interaction):
    await interaction.response.send_message(f'쉬어!')

@client.tree.command(name='일정', description='돌승엽이 KBO 경기 일정을 당신에게 보여줍니다.')
@app_commands.describe(args_date='[오늘|내일|모레]를 선택해 언제 일정을 확인할지 선택하세요.')
async def schedule(interaction: discord.Interaction, args_date: Literal['오늘', '내일', '모레']):
    selected_day = {'오늘':0,'내일':1,'모레':2}
    selected_date = (datetime.today()+timedelta(days=selected_day[args_date]))

    embed = discord.Embed(title=f'{selected_date.strftime("%m월 %d일")} {days[selected_date.weekday()]}요일 KBO 경기 일정',url=f'https://m.sports.naver.com/kbaseball/schedule/index?date={selected_date.strftime("%Y-%m-%d")}', color=0x00AEEF)

    from_db_result = database.select_game_and_scord(selected_date.strftime('%m%d'))
    if selected_date.weekday() == 0:
        await interaction.response.send_message('경기가 없는 날입니다.')
        return
    if from_db_result is None:
        await interaction.response.send_message('일정을 찾을 수 없습니다.')
        return

    embed_title= [ f'{"목차":<5}{"시간"}', f'{"경기"}', f'{"구장":<5}{"비고":<5}']
    str = ['', '', '']
    for i in range(len(from_db_result)):
        str[0] = str[0] + f'{emoji[i+1]:<5} {from_db_result[i][1]}\n'
        score = [from_db_result[i][7] if from_db_result[i][7] != -1 else '', from_db_result[i][8] if from_db_result[i][8] != -1 else '']
        str[1] = str[1] + f'{from_db_result[i][2]:<10}{logo_emoji[from_db_result[i][2]]}{score[0]} vs {score[1]}{from_db_result[i][3]:<10}{logo_emoji[from_db_result[i][3]]}\n'
        str[2] = str[2] + f'{from_db_result[i][4]:<5}{from_db_result[i][5]:<5}\n'

    embed.set_footer(text='Created').timestamp = datetime.now()
    embed.add_field(name=embed_title[0], value=str[0], inline=True)
    embed.add_field(name=embed_title[1], value=str[1], inline=True)
    embed.add_field(name=embed_title[2], value=str[2], inline=True)

    await interaction.response.send_message(embed=embed)




client.run(TOKEN)