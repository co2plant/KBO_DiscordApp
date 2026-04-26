const assert = require('node:assert/strict');
const test = require('node:test');

const { formatScheduleMatchup, parseScheduleScore, shouldHideScheduleScore } = require('../src/render/schedule');
const { buildStandingsLines, findStandingsTeam, isHotStreak } = require('../src/render/standings');

test('parseScheduleScore hides -1 sentinel as zero before rendering vs', () => {
  assert.equal(parseScheduleScore(-1), 0);
  assert.equal(parseScheduleScore('-1'), 0);
});

test('formatScheduleMatchup renders pending -1 scores as vs', () => {
  const selectedDate = new Date(Date.UTC(2099, 3, 22));
  const row = {
    time: '18:30',
    away: '한화',
    home: 'LG',
    stadium: '잠실',
    remarks: '-',
    away_score: -1,
    home_score: -1,
  };

  const rendered = formatScheduleMatchup(selectedDate, row, new Date(Date.UTC(2099, 3, 22, 0, 0)));

  assert.match(rendered, /vs/);
  assert.doesNotMatch(rendered, /-1/);
});

test('shouldHideScheduleScore does not hide completed scores', () => {
  const selectedDate = new Date(Date.UTC(2099, 3, 22));

  assert.equal(shouldHideScheduleScore(selectedDate, '18:30', '-', 3, 2), false);
});

test('buildStandingsLines and helpers preserve standings rendering contract', () => {
  const rows = [{ id: '1', team: '한화', win: 10, lose: 5, draw: 1, rate: '0.667', last_10: '7-3', streak: '3승', home: '5-2', away: '5-3' }];

  assert.equal(isHotStreak('3승'), true);
  assert.equal(isHotStreak('2승'), false);
  assert.equal(findStandingsTeam(rows, ' 한화 '), rows[0]);
  assert.deepEqual(buildStandingsLines(rows), [
    '순위 | 팀 | 승 | 패 | 무 | 승률',
    ':one: | <:HH:1242717656214143056> 한화 🔥 | 10 | 5 | 1 | 0.667',
  ]);
});
