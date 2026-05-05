import fs from 'node:fs';

function loadConfigFile() {
  if (!fs.existsSync('config.json')) {
    return {};
  }

  return JSON.parse(fs.readFileSync('config.json', 'utf8'));
}

function coalesce(...values) {
  return values.find((value) => value !== undefined && value !== null && value !== '');
}

const fileConfig = loadConfigFile();
const discord = fileConfig.DISCORD ?? {};
const maria = fileConfig.MARIA ?? {};

export const config = {
  discordToken: coalesce(process.env.DISCORD_TOKEN, discord.TOKEN),
  discordChannelId: coalesce(process.env.DISCORD_CHANNEL_ID, discord.CHANNEL_ID),
  discordGuildId: coalesce(process.env.DISCORD_GUILD_ID, discord.GUILD_ID),
  db: {
    host: coalesce(process.env.DB_HOST, process.env.MARIA_HOST, maria.HOST, '127.0.0.1'),
    user: coalesce(process.env.DB_USER, process.env.MARIA_USER, maria.USER),
    password: coalesce(process.env.DB_PASSWORD, process.env.MARIA_PASSWORD, maria.PASSWORD),
    database: coalesce(process.env.DB_NAME, process.env.MARIA_DB, maria.DB)
  },
  chromiumPath: coalesce(process.env.PUPPETEER_EXECUTABLE_PATH, process.env.CHROME_BIN, '/usr/bin/chromium')
};

export function assertConfig() {
  if (!config.discordToken) {
    throw new Error('Missing Discord token. Set DISCORD_TOKEN env or provide config.json');
  }

  if (!config.discordGuildId) {
    throw new Error('Missing Discord guild id. Set DISCORD_GUILD_ID env or provide config.json');
  }

  for (const [name, value] of Object.entries(config.db)) {
    if (!value) {
      throw new Error(`Missing DB setting: ${name}`);
    }
  }
}
