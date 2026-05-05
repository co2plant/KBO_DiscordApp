import { logoEmoji } from '../constants.js';
import { normalizeTeamName } from './formatters.js';

const MAX_AUTOCOMPLETE_CHOICES = 25;

export function normalizeTeamInput(teamName) {
  const normalized = normalizeTeamName(teamName);
  return Object.keys(logoEmoji).find((team) => normalizeTeamName(team) === normalized) ?? null;
}

export function buildTeamAutocompleteChoices(input = '') {
  const normalizedInput = normalizeTeamName(input);
  const teams = Object.keys(logoEmoji);
  const filteredTeams = normalizedInput
    ? teams.filter((team) => normalizeTeamName(team).includes(normalizedInput))
    : teams;

  return filteredTeams.slice(0, MAX_AUTOCOMPLETE_CHOICES).map((team) => ({
    name: team,
    value: team
  }));
}

export async function resolvePreferredTeam(options) {
  const rawTeam = String(options.providedTeam ?? '').trim();
  const providedTeam = normalizeTeamInput(options.providedTeam);
  if (providedTeam) {
    return providedTeam;
  }
  if (rawTeam) {
    return null;
  }

  const preference = await options.database.selectUserPreference(options.discordUserId);
  return preference?.favoriteTeam ? normalizeTeamInput(preference.favoriteTeam) : null;
}
