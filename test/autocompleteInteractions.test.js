import assert from 'node:assert/strict';
import test from 'node:test';

import {
  handleAutocomplete,
  isAutocompleteInteraction
} from '../src/interactions/autocompleteInteractions.js';

test('isAutocompleteInteraction detects autocomplete interactions', () => {
  assert.equal(isAutocompleteInteraction({ isAutocomplete: () => true }), true);
  assert.equal(isAutocompleteInteraction({ isAutocomplete: () => false }), false);
  assert.equal(isAutocompleteInteraction({}), false);
});

test('handleAutocomplete responds with team choices for focused team option', async () => {
  let response = null;
  const interaction = {
    options: {
      getFocused() {
        return { name: 'team', value: 'ki' };
      }
    },
    async respond(choices) {
      response = choices;
    }
  };

  await handleAutocomplete(interaction);

  assert.deepEqual(response[0], { name: 'KIA', value: 'KIA' });
});

test('handleAutocomplete responds with empty choices for unsupported options', async () => {
  let response = null;
  const interaction = {
    options: {
      getFocused() {
        return { name: 'name', value: '홍' };
      }
    },
    async respond(choices) {
      response = choices;
    }
  };

  await handleAutocomplete(interaction);

  assert.deepEqual(response, []);
});

test('handleAutocomplete responds with cached player name choices for player command', async () => {
  let response = null;
  const interaction = {
    commandName: '선수',
    options: {
      getFocused() {
        return { name: 'name', value: '홍' };
      }
    },
    async respond(choices) {
      response = choices;
    }
  };
  const database = {
    async selectPlayerAutocomplete(keyword) {
      assert.equal(keyword, '홍');
      return [{ name: '홍창기', teams: 'LG' }];
    }
  };

  await handleAutocomplete(interaction, { database });

  assert.deepEqual(response, [{ name: '홍창기 (LG)', value: '홍창기' }]);
});
