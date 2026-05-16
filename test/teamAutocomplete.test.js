import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildTeamAutocompleteChoices,
  resolvePreferredTeam
} from '../src/utils/teamAutocomplete.js';

test('buildTeamAutocompleteChoices returns matching team choices for slash command autocomplete', () => {
  const choices = buildTeamAutocompleteChoices('ki');

  assert.deepEqual(choices[0], { name: 'KIA', value: 'KIA' });
  assert.equal(choices.length <= 25, true);
});

test('buildTeamAutocompleteChoices returns all teams when input is empty', () => {
  const choices = buildTeamAutocompleteChoices('');

  assert.equal(choices.length >= 10, true);
  assert.equal(choices.every((choice) => choice.name && choice.value), true);
});

test('resolvePreferredTeam uses provided team before user default team', async () => {
  const database = {
    async selectUserPreference() {
      throw new Error('default team should not be queried when team is provided');
    }
  };

  const team = await resolvePreferredTeam({
    providedTeam: 'kia',
    discordUserId: 'user-1',
    database
  });

  assert.equal(team, 'KIA');
});

test('resolvePreferredTeam rejects invalid provided team instead of falling back silently', async () => {
  const database = {
    async selectUserPreference() {
      return { favoriteTeam: 'LG' };
    }
  };

  const team = await resolvePreferredTeam({
    providedTeam: '없는팀',
    discordUserId: 'user-1',
    database
  });

  assert.equal(team, null);
});

test('resolvePreferredTeam falls back to the saved default team', async () => {
  const database = {
    async selectUserPreference(discordUserId) {
      assert.equal(discordUserId, 'user-1');
      return { favoriteTeam: 'LG' };
    }
  };

  const team = await resolvePreferredTeam({
    providedTeam: '',
    discordUserId: 'user-1',
    database
  });

  assert.equal(team, 'LG');
});
