const fs = require('node:fs');
const path = require('node:path');

const { REST, Routes } = require('discord.js');

const { config } = require('./src/config');

function loadCommandData() {
  const commands = [];
  const commandsPath = path.join(__dirname, 'commands');
  const commandFiles = fs.readdirSync(commandsPath).filter(file => file.endsWith('.js'));

  for (const file of commandFiles) {
    const filePath = path.join(commandsPath, file);
    const command = require(filePath);
    if (!command.data) {
      throw new Error(`Missing command data: ${filePath}`);
    }

    commands.push(typeof command.data.toJSON === 'function' ? command.data.toJSON() : command.data);
  }

  return commands;
}

async function deployCommands() {
  const commands = loadCommandData();
  const rest = new REST({ version: '10' }).setToken(config.discordToken);

  console.log(`Started refreshing ${commands.length} application (/) commands.`);
  const data = await rest.put(
    Routes.applicationGuildCommands(config.discordClientId, config.discordGuildId),
    { body: commands },
  );
  console.log(`Successfully reloaded ${data.length} application (/) commands.`);
}

if (require.main === module) {
  deployCommands().catch(error => {
    console.error(error);
    process.exitCode = 1;
  });
}

module.exports = { deployCommands, loadCommandData };
