require('dotenv').config();

function coalesce(...values) {
  for (const value of values) {
    if (value !== undefined && value !== null && value !== '') {
      return value;
    }
  }
  return undefined;
}

function requireSetting(name, value) {
  if (value === undefined || value === null || value === '') {
    throw new Error(`Missing setting: ${name}`);
  }
  return value;
}

function readInteger(name, value, defaultValue = 0) {
  const rawValue = coalesce(value, String(defaultValue));
  const parsedValue = Number.parseInt(rawValue, 10);
  if (Number.isNaN(parsedValue)) {
    throw new Error(`Invalid integer setting: ${name}`);
  }
  return parsedValue;
}

const config = {
  discordToken: requireSetting('DISCORD_TOKEN', process.env.DISCORD_TOKEN),
  discordClientId: requireSetting('DISCORD_CLIENT_ID', process.env.DISCORD_CLIENT_ID),
  discordChannelId: readInteger('DISCORD_CHANNEL_ID', process.env.DISCORD_CHANNEL_ID),
  discordGuildId: requireSetting('DISCORD_GUILD_ID', process.env.DISCORD_GUILD_ID),
  dbHost: coalesce(process.env.DB_HOST, process.env.MARIA_HOST, '127.0.0.1'),
  dbUser: requireSetting('DB_USER', coalesce(process.env.DB_USER, process.env.MARIA_USER)),
  dbPassword: requireSetting('DB_PASSWORD', coalesce(process.env.DB_PASSWORD, process.env.MARIA_PASSWORD)),
  dbName: requireSetting('DB_NAME', coalesce(process.env.DB_NAME, process.env.MARIA_DB)),
};

module.exports = { config, coalesce, readInteger, requireSetting };
