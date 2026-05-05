import {
  ActivityType,
  Client,
  Events,
  GatewayIntentBits,
  REST,
  Routes
} from 'discord.js';

import { assertConfig, config } from './config.js';
import { KST_OFFSET_MS, nowKst, toMmdd } from './constants.js';
import { createCommands } from './commands/kboCommands.js';
import * as crawler from './services/kboCrawler.js';
import * as database from './services/database.js';
import { ensureDataReady } from './services/dataReady.js';

assertConfig();

const client = new Client({ intents: [GatewayIntentBits.Guilds] });
const commands = createCommands({ database, crawler });
const commandMap = new Map(commands.map((command) => [command.data.name, command]));

async function registerGuildCommands(applicationId) {
  const rest = new REST({ version: '10' }).setToken(config.discordToken);
  await rest.put(
    Routes.applicationGuildCommands(applicationId, config.discordGuildId),
    { body: commands.map((command) => command.data.toJSON()) }
  );
}

function msUntilNextKstHour(hour) {
  const now = new Date();
  const shiftedNow = new Date(now.getTime() + KST_OFFSET_MS);
  const shiftedNext = new Date(shiftedNow.getTime());
  shiftedNext.setUTCHours(hour, 0, 0, 0);
  if (shiftedNext <= shiftedNow) {
    shiftedNext.setUTCDate(shiftedNext.getUTCDate() + 1);
  }
  return shiftedNext.getTime() - shiftedNow.getTime();
}

function scheduleDailyKst(hour, task) {
  const run = async () => {
    try {
      await task();
    } finally {
      setTimeout(run, msUntilNextKstHour(hour));
    }
  };

  setTimeout(run, msUntilNextKstHour(hour));
}

async function dailyRefresh() {
  await crawler.updateStandings(database);
  await crawler.updateScheduleOnce(toMmdd(nowKst()), database);
}

client.once(Events.ClientReady, async (readyClient) => {
  console.log(`Logged in as ${readyClient.user.tag} (ID: ${readyClient.user.id})`);
  readyClient.user.setActivity('전략 분석', { type: ActivityType.Playing });

  await registerGuildCommands(readyClient.user.id);
  await ensureDataReady(database, crawler);
  scheduleDailyKst(6, dailyRefresh);
  console.log('KBO bot is ready.');
});

client.on(Events.InteractionCreate, async (interaction) => {
  if (!interaction.isChatInputCommand()) {
    return;
  }

  const command = commandMap.get(interaction.commandName);
  if (!command) {
    return;
  }

  try {
    await command.execute(interaction);
  } catch (error) {
    console.error(`Command failed: ${interaction.commandName}`, error);
    const message = '명령 처리 중 오류가 발생했습니다.';
    if (interaction.deferred || interaction.replied) {
      await interaction.editReply(message);
    } else {
      await interaction.reply({ content: message, ephemeral: true });
    }
  }
});

process.on('SIGINT', async () => {
  await database.closePool();
  client.destroy();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  await database.closePool();
  client.destroy();
  process.exit(0);
});

client.login(config.discordToken);
