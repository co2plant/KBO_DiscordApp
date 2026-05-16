import assert from 'node:assert/strict';
import test from 'node:test';

import * as dataReady from '../src/services/dataReady.js';

test('selectScheduleRowsForCommand refreshes live scores before returning schedule rows during live window', async (t) => {
  const selectedDateKey = '0506';
  const selectedDate = new Date(Date.UTC(2026, 4, 6, 0, 0));
  const beforeRefresh = [
    {
      time: '14:00',
      away: '두산',
      home: 'LG',
      stadium: '잠실',
      remarks: '-',
      awayScore: 0,
      homeScore: 0
    }
  ];
  const afterRefresh = [
    {
      ...beforeRefresh[0],
      remarks: '3회초',
      awayScore: 2,
      homeScore: 1
    }
  ];
  const events = [];

  const database = {
    async hasScheduleDataForDate(dateKey) {
      events.push(`has:${dateKey}`);
      return true;
    },
    async selectGamesAndScores(dateKey) {
      events.push(`select:${dateKey}`);
      return events.includes(`update:${dateKey}`) ? afterRefresh : beforeRefresh;
    }
  };
  const crawler = {
    async updateLiveScores(dateKey) {
      events.push(`update:${dateKey}`);
      return 1;
    }
  };
  t.mock.method(console, 'log', () => {});

  assert.equal(typeof dataReady.selectScheduleRowsForCommand, 'function');

  const rows = await dataReady.selectScheduleRowsForCommand(database, crawler, selectedDateKey, selectedDate, {
    now: new Date(Date.UTC(2026, 4, 6, 13, 55))
  });

  assert.equal(rows[0].awayScore, 2);
  assert.equal(rows[0].homeScore, 1);
  assert.equal(rows[0].remarks, '3회초');
  assert.deepEqual(events, ['has:0506', 'select:0506', 'update:0506', 'select:0506']);
});
