import assert from 'node:assert/strict';
import test from 'node:test';

import {
  findTeamGames,
  formatScoreLine,
  isHotStreak,
  shouldRefreshLiveScores
} from '../src/utils/formatters.js';

test('formatScoreLine hides sentinel scores before game time', () => {
  const selectedDate = new Date(Date.UTC(2026, 4, 5, 0, 0));
  const now = new Date(Date.UTC(2026, 4, 5, 4, 0));
  const row = {
    time: '14:00',
    away: 'NC',
    home: 'LG',
    stadium: '잠실',
    remarks: '-',
    awayScore: -1,
    homeScore: -1
  };

  const rendered = formatScoreLine(selectedDate, row, { now });

  assert.match(rendered, /14:00/);
  assert.match(rendered, /NC vs .*LG/);
  assert.match(rendered, /경기 전/);
  assert.doesNotMatch(rendered, /-1/);
});

test('findTeamGames matches home and away case-insensitively', () => {
  const rows = [
    { id: '050500', away: 'NC', home: 'LG' },
    { id: '050501', away: 'KIA', home: '한화' },
    { id: '050502', away: 'KT', home: 'NC' }
  ];

  assert.deepEqual(findTeamGames(rows, 'nc').map((row) => row.id), ['050500', '050502']);
});

test('isHotStreak marks only three or more consecutive wins', () => {
  assert.equal(isHotStreak('3연승'), true);
  assert.equal(isHotStreak('2연승'), false);
  assert.equal(isHotStreak('3연패'), false);
});

test('shouldRefreshLiveScores starts inside live window and skips final games', () => {
  const selectedDate = new Date(Date.UTC(2026, 4, 5, 0, 0));
  const now = new Date(Date.UTC(2026, 4, 5, 13, 55));
  const rows = [
    { time: '14:00', remarks: '-', away: 'NC', home: 'LG' }
  ];

  assert.equal(shouldRefreshLiveScores(selectedDate, rows, { now }), true);
  assert.equal(
    shouldRefreshLiveScores(selectedDate, [{ ...rows[0], remarks: '경기종료' }], { now }),
    false
  );
});
