const fs = require('node:fs');
const path = require('node:path');

const { Client, Collection, Events, GatewayIntentBits, ActivityType } = require('discord.js');

const { config } = require('./src/config');
const database = require('./src/database');
const kboCrawler = require('./src/crawler/kboCrawler');
const { formatMonthDay, nowKst } = require('./src/time');

const client = new Client({ intents: [GatewayIntentBits.Guilds] });
client.commands = new Collection();

let dataReady = false;
let dataReadyPromise = null;

function loadCommands() {
  const commandsPath = path.join(__dirname, 'commands');
  const commandFiles = fs.readdirSync(commandsPath).filter(file => file.endsWith('.js'));

  for (const file of commandFiles) {
    const filePath = path.join(commandsPath, file);
    const command = require(filePath);
    if (!command.data || !command.execute) {
      throw new Error(`Invalid command module: ${filePath}`);
    }
    const commandData = typeof command.data.toJSON === 'function' ? command.data.toJSON() : command.data;
    client.commands.set(commandData.name, command);
  }
}

async function ensureDataReady() {
  if (dataReady) {
    return;
  }

  if (dataReadyPromise) {
    await dataReadyPromise;
    return;
  }

  dataReadyPromise = (async () => {
    await database.ensureSchema();

    if (!await database.hasStandingsData()) {
      console.log('Bootstrapping standings data...');
      await kboCrawler.insertStandings();
    }

    if (!await database.hasScheduleData()) {
      console.log('Bootstrapping schedule data...');
      await kboCrawler.insertScheduleMonth();
    }

    dataReady = true;
  })();

  try {
    await dataReadyPromise;
  } finally {
    dataReadyPromise = null;
  }
}

async function updateTables() {
  await kboCrawler.updateStandings();
  await kboCrawler.updateScheduleOnce(formatMonthDay(nowKst()));
}

function scheduleDailyUpdate() {
  const run = async () => {
    try {
      await updateTables();
    } catch (error) {
      console.error('Daily KBO table update failed:', error);
    } finally {
      scheduleDailyUpdate();
    }
  };

  const now = nowKst();
  const nextRun = new Date(now.getTime());
  nextRun.setUTCHours(6, 0, 0, 0);
  if (nextRun <= now) {
    nextRun.setUTCDate(nextRun.getUTCDate() + 1);
  }

  setTimeout(run, nextRun.getTime() - now.getTime());
}

client.once(Events.ClientReady, async readyClient => {
  console.log(`Logged in as ${readyClient.user.tag} (ID: ${readyClient.user.id})`);
  readyClient.user.setPresence({
    status: 'online',
    activities: [{ name: '전략 분석', type: ActivityType.Playing }],
  });

  await ensureDataReady();
  scheduleDailyUpdate();
});

client.on(Events.InteractionCreate, async interaction => {
  if (!interaction.isChatInputCommand()) {
    return;
  }

  const command = client.commands.get(interaction.commandName);
  if (!command) {
    return;
  }

  try {
    await command.execute(interaction, { ensureDataReady });
  } catch (error) {
    console.error(`Command ${interaction.commandName} failed:`, error);
    const message = '명령 처리 중 오류가 발생했습니다.';
    if (interaction.deferred || interaction.replied) {
      await interaction.followUp({ content: message, ephemeral: true });
    } else {
      await interaction.reply({ content: message, ephemeral: true });
    }
  }
});

loadCommands();
client.login(config.discordToken);

module.exports = { ensureDataReady, loadCommands, scheduleDailyUpdate, updateTables };
