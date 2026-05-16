import { buildTeamAutocompleteChoices } from '../utils/teamAutocomplete.js';
import { buildPlayerAutocompleteChoices } from '../utils/playerAutocomplete.js';

export function isAutocompleteInteraction(interaction) {
  return typeof interaction.isAutocomplete === 'function' && interaction.isAutocomplete();
}

export async function handleAutocomplete(interaction, dependencies = {}) {
  const focused = interaction.options.getFocused(true);
  if (focused.name === 'team') {
    await interaction.respond(buildTeamAutocompleteChoices(focused.value));
    return;
  }

  if (
    focused.name === 'name'
    && interaction.commandName === '선수'
    && dependencies.database?.selectPlayerAutocomplete
  ) {
    const players = await dependencies.database.selectPlayerAutocomplete(focused.value);
    await interaction.respond(buildPlayerAutocompleteChoices(players));
    return;
  }

  await interaction.respond([]);
}
