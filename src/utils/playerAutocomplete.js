const MAX_AUTOCOMPLETE_CHOICES = 25;

export function buildPlayerAutocompleteChoices(players = []) {
  return players.slice(0, MAX_AUTOCOMPLETE_CHOICES).map((player) => {
    const teams = player.teams ? ` (${player.teams})` : '';
    return {
      name: `${player.name}${teams}`,
      value: player.name
    };
  });
}
