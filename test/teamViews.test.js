import assert from 'node:assert/strict';
import test from 'node:test';

import { buildTeamRecordFields } from '../src/utils/teamViews.js';

test('buildTeamRecordFields stacks home and away under streak', () => {
  const fields = buildTeamRecordFields({
    id: '5',
    win: 32,
    lose: 15,
    draw: 16,
    rate: '0.484',
    last10: '5승1무4패',
    streak: '1승',
    home: '9-1-5',
    away: '6-0-11'
  });

  assert.deepEqual(fields, [
    {
      name: '요약',
      value: '5위 · 32승 15패 16무 (0.484)',
      inline: false
    },
    { name: '최근 10경기', value: '5승1무4패', inline: true },
    {
      name: '연속',
      value: '1승\n**홈**\n9-1-5\n**원정**\n6-0-11',
      inline: true
    }
  ]);
});
