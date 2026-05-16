const MAX_OPTIONS_JSON_LENGTH = 2048;
const MAX_ERROR_MESSAGE_LENGTH = 512;

function truncate(value, maxLength) {
  const text = String(value ?? '');
  return text.length > maxLength ? text.slice(0, maxLength) : text;
}

function optionValue(option) {
  if (option.options?.length) {
    return Object.fromEntries(option.options.map((child) => [child.name, optionValue(child)]));
  }

  return option.value ?? '';
}

function truncateOptionsJson(json) {
  let previewLength = Math.max(0, MAX_OPTIONS_JSON_LENGTH - 64);

  while (previewLength >= 0) {
    const output = JSON.stringify({
      _truncated: true,
      preview: json.slice(0, previewLength)
    });

    if (output.length <= MAX_OPTIONS_JSON_LENGTH) {
      return output;
    }

    previewLength -= 128;
  }

  return '{"_truncated":true}';
}

function serializeOptions(interaction) {
  const options = interaction.options?.data ?? [];
  const payload = Object.fromEntries(options.map((option) => [option.name, optionValue(option)]));
  const json = JSON.stringify(payload);
  return json.length > MAX_OPTIONS_JSON_LENGTH ? truncateOptionsJson(json) : json;
}

export function buildCommandLogEntry(interaction, result) {
  return {
    interactionId: String(interaction.id ?? ''),
    commandName: String(interaction.commandName ?? ''),
    discordUserId: String(interaction.user?.id ?? ''),
    guildId: String(interaction.guildId ?? ''),
    channelId: String(interaction.channelId ?? ''),
    optionsJson: serializeOptions(interaction),
    status: String(result.status ?? 'unknown'),
    durationMs: Number(result.durationMs ?? 0),
    errorMessage: truncate(result.error?.message ?? result.errorMessage ?? '', MAX_ERROR_MESSAGE_LENGTH)
  };
}

export async function recordCommandLog(database, interaction, result) {
  try {
    await database.insertCommandLog(buildCommandLogEntry(interaction, result));
  } catch (error) {
    console.log(`Failed to record command log: ${error.message}`);
  }
}
