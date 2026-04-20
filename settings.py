import json
import os
from typing import Any, Dict


def _load_config_file(path: str = 'config.json') -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _coalesce(*values):
    for value in values:
        if value is not None and value != '':
            return value
    return None


_config = _load_config_file()
_discord = _config.get('DISCORD', {})
_maria = _config.get('MARIA', {})

DISCORD_TOKEN = _coalesce(os.getenv('DISCORD_TOKEN'), _discord.get('TOKEN'))
DISCORD_CHANNEL_ID = int(_coalesce(os.getenv('DISCORD_CHANNEL_ID'), _discord.get('CHANNEL_ID'), 0))
DISCORD_GUILD_ID = int(_coalesce(os.getenv('DISCORD_GUILD_ID'), _discord.get('GUILD_ID'), 0))

DB_HOST = _coalesce(os.getenv('DB_HOST'), os.getenv('MARIA_HOST'), _maria.get('HOST'), '127.0.0.1')
DB_USER = _coalesce(os.getenv('DB_USER'), os.getenv('MARIA_USER'), _maria.get('USER'))
DB_PASSWORD = _coalesce(os.getenv('DB_PASSWORD'), os.getenv('MARIA_PASSWORD'), _maria.get('PASSWORD'))
DB_NAME = _coalesce(os.getenv('DB_NAME'), os.getenv('MARIA_DB'), _maria.get('DB'))


if not DISCORD_TOKEN:
    raise RuntimeError('Missing Discord token. Set DISCORD_TOKEN env or provide config.json')

for key, value in {
    'DB_USER': DB_USER,
    'DB_PASSWORD': DB_PASSWORD,
    'DB_NAME': DB_NAME,
}.items():
    if not value:
        raise RuntimeError(f'Missing DB setting: {key}. Set env or provide config.json')
