import assert from 'node:assert/strict';
import test from 'node:test';

import {
  ALERT_TYPES,
  buildDueAlertDeliveries,
  normalizeAlertTeam
} from '../src/services/alerts.js';
import { runAlertCheck } from '../src/services/alertWorker.js';

test('buildDueAlertDeliveries creates a start alert during the configured lead window', () => {
  const selectedDate = new Date(Date.UTC(2026, 4, 5, 0, 0));
  const games = [
    {
      id: '050500',
      time: '14:00',
      away: 'KIA',
      home: 'LG',
      stadium: '잠실',
      remarks: '-',
      awayScore: 0,
      homeScore: 0
    }
  ];
  const alerts = [
    {
      discordUserId: 'user-1',
      alertType: ALERT_TYPES.GAME_START,
      team: 'KIA',
      notifyBeforeMinutes: 10
    }
  ];

  const due = buildDueAlertDeliveries(alerts, games, selectedDate, {
    now: new Date(Date.UTC(2026, 4, 5, 13, 50))
  });

  assert.equal(due.length, 1);
  assert.equal(due[0].deliveryKey, 'user-1:game_start:2026-05-05:050500');
  assert.equal(due[0].discordUserId, 'user-1');
  assert.match(due[0].message, /KIA/);
  assert.match(due[0].message, /10분 전/);
});

test('buildDueAlertDeliveries creates a result alert after the subscribed team game ends', () => {
  const selectedDate = new Date(Date.UTC(2026, 4, 5, 0, 0));
  const games = [
    {
      id: '050501',
      time: '14:00',
      away: 'KIA',
      home: 'LG',
      stadium: '잠실',
      remarks: '경기종료',
      awayScore: 3,
      homeScore: 2
    }
  ];
  const alerts = [
    {
      discordUserId: 'user-1',
      alertType: ALERT_TYPES.GAME_RESULT,
      team: 'LG',
      notifyBeforeMinutes: 10
    }
  ];

  const due = buildDueAlertDeliveries(alerts, games, selectedDate, {
    now: new Date(Date.UTC(2026, 4, 5, 17, 0))
  });

  assert.equal(due.length, 1);
  assert.equal(due[0].deliveryKey, 'user-1:game_result:2026-05-05:050501');
  assert.match(due[0].message, /경기 종료/);
  assert.match(due[0].message, /3 vs 2/);
});

test('normalizeAlertTeam returns the canonical team key for alert commands', () => {
  assert.equal(normalizeAlertTeam('kia'), 'KIA');
  assert.equal(normalizeAlertTeam(' LG '), 'LG');
  assert.equal(normalizeAlertTeam('없는팀'), null);
});

test('runAlertCheck claims a due delivery before sending the DM', async (t) => {
  t.mock.method(console, 'log', () => {});
  const events = [];
  const selectedDate = new Date(Date.UTC(2026, 4, 5, 0, 0));
  const database = {
    async hasScheduleDataForDate() {
      return true;
    },
    async selectGamesAndScores() {
      return [
        {
          id: '050500',
          time: '14:00',
          away: 'KIA',
          home: 'LG',
          stadium: '잠실',
          remarks: '-',
          awayScore: 0,
          homeScore: 0
        }
      ];
    },
    async selectEnabledUserAlerts() {
      return [
        {
          discordUserId: 'user-1',
          alertType: ALERT_TYPES.GAME_START,
          team: 'KIA',
          notifyBeforeMinutes: 10
        }
      ];
    },
    async claimAlertDelivery(delivery) {
      events.push(`claim:${delivery.deliveryKey}`);
      return true;
    },
    async markAlertDeliverySent(deliveryKey) {
      events.push(`sent:${deliveryKey}`);
    },
    async markAlertDeliveryFailed(deliveryKey) {
      events.push(`failed:${deliveryKey}`);
    }
  };
  const crawler = {
    async updateLiveScores() {
      events.push('crawl');
      return 0;
    }
  };
  const client = {
    users: {
      async fetch(userId) {
        events.push(`fetch:${userId}`);
        return {
          async send(message) {
            events.push(`dm:${message.includes('KIA')}`);
          }
        };
      }
    }
  };

  const result = await runAlertCheck({ client, database, crawler }, {
    now: new Date(Date.UTC(2026, 4, 5, 13, 50)),
    selectedDate,
    selectedDateKey: '0505'
  });

  assert.equal(result.sent, 1);
  assert.deepEqual(events, [
    'crawl',
    'claim:user-1:game_start:2026-05-05:050500',
    'fetch:user-1',
    'dm:true',
    'sent:user-1:game_start:2026-05-05:050500'
  ]);
});

test('runAlertCheck skips DM delivery when the delivery key was already claimed', async (t) => {
  t.mock.method(console, 'log', () => {});
  const events = [];
  const selectedDate = new Date(Date.UTC(2026, 4, 5, 0, 0));
  const database = {
    async hasScheduleDataForDate() {
      return true;
    },
    async selectGamesAndScores() {
      return [
        {
          id: '050500',
          time: '14:00',
          away: 'KIA',
          home: 'LG',
          stadium: '잠실',
          remarks: '-',
          awayScore: 0,
          homeScore: 0
        }
      ];
    },
    async selectEnabledUserAlerts() {
      return [
        {
          discordUserId: 'user-1',
          alertType: ALERT_TYPES.GAME_START,
          team: 'KIA',
          notifyBeforeMinutes: 10
        }
      ];
    },
    async claimAlertDelivery(delivery) {
      events.push(`claim:${delivery.deliveryKey}`);
      return false;
    },
    async markAlertDeliverySent(deliveryKey) {
      events.push(`sent:${deliveryKey}`);
    },
    async markAlertDeliveryFailed(deliveryKey) {
      events.push(`failed:${deliveryKey}`);
    }
  };
  const crawler = {
    async updateLiveScores() {
      events.push('crawl');
      return 0;
    }
  };
  const client = {
    users: {
      async fetch(userId) {
        events.push(`fetch:${userId}`);
        return {
          async send() {
            events.push('dm');
          }
        };
      }
    }
  };

  const result = await runAlertCheck({ client, database, crawler }, {
    now: new Date(Date.UTC(2026, 4, 5, 13, 50)),
    selectedDate,
    selectedDateKey: '0505'
  });

  assert.equal(result.sent, 0);
  assert.equal(result.skipped, 1);
  assert.deepEqual(events, [
    'crawl',
    'claim:user-1:game_start:2026-05-05:050500'
  ]);
});
