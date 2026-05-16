import assert from 'node:assert/strict';
import test from 'node:test';

import { buildPlayerAutocompleteChoices } from '../src/utils/playerAutocomplete.js';

test('buildPlayerAutocompleteChoices renders player names with team hints', () => {
  const choices = buildPlayerAutocompleteChoices([
    { name: '홍창기', teams: 'LG' },
    { name: '김민수', teams: 'KIA, KT' }
  ]);

  assert.deepEqual(choices, [
    { name: '홍창기 (LG)', value: '홍창기' },
    { name: '김민수 (KIA, KT)', value: '김민수' }
  ]);
});

test('buildPlayerAutocompleteChoices limits choices for Discord autocomplete', () => {
  const players = Array.from({ length: 30 }, (_, index) => ({
    name: `선수${index}`,
    teams: 'KIA'
  }));

  assert.equal(buildPlayerAutocompleteChoices(players).length, 25);
});
