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
  assert.match(due[0].message, /경기 종료 요약/);
  assert.match(due[0].message, /3 vs 2/);
  assert.match(due[0].message, /LG가 1점 차로 패배했습니다/);
  assert.doesNotMatch(due[0].message, /역전은/);
});

test('buildDueAlertDeliveries includes lead-change history in result summaries', () => {
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
      homeScore: 5
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
  const resultEventHistoryByGameId = new Map([
    ['050501', [
      {
        gameId: '050501',
        time: '14:00',
        team: 'KIA',
        previousLeaderTeam: 'LG',
        away: 'KIA',
        home: 'LG',
        stadium: '잠실',
        remarks: '4회초',
        awayScore: 3,
        homeScore: 2
      },
      {
        gameId: '050501',
        time: '14:00',
        team: 'LG',
        previousLeaderTeam: 'KIA',
        away: 'KIA',
        home: 'LG',
        stadium: '잠실',
        remarks: '7회말',
        awayScore: 3,
        homeScore: 5
      }
    ]]
  ]);

  const due = buildDueAlertDeliveries(alerts, games, selectedDate, {
    now: new Date(Date.UTC(2026, 4, 5, 17, 0)),
    resultEventHistoryByGameId
  });

  assert.equal(due.length, 1);
  assert.match(due[0].message, /LG가 2점 차로 승리했습니다/);
  assert.match(due[0].message, /역전은 2번 있었습니다/);
  assert.match(due[0].message, /마지막 역전은 7회말 LG가 5-3으로 앞선 장면입니다/);
});

test('buildDueAlertDeliveries summarizes tied result alerts', () => {
  const selectedDate = new Date(Date.UTC(2026, 4, 5, 0, 0));
  const games = [
    {
      id: '050502',
      time: '18:30',
      away: 'KIA',
      home: 'LG',
      stadium: '잠실',
      remarks: '경기종료',
      awayScore: 3,
      homeScore: 3
    }
  ];
  const alerts = [
    {
      discordUserId: 'user-1',
      alertType: ALERT_TYPES.GAME_RESULT,
      team: 'KIA',
      notifyBeforeMinutes: 10
    }
  ];

  const due = buildDueAlertDeliveries(alerts, games, selectedDate, {
    now: new Date(Date.UTC(2026, 4, 5, 22, 0))
  });

  assert.equal(due.length, 1);
  assert.match(due[0].message, /KIA가 3 vs 3 무승부로 경기를 마쳤습니다/);
});

test('buildDueAlertDeliveries sends cancellation result alerts without win or lead-change text', () => {
  const selectedDate = new Date(Date.UTC(2026, 4, 5, 0, 0));
  const games = [
    {
      id: '050503',
      time: '18:30',
      away: 'KIA',
      home: 'LG',
      stadium: '잠실',
      remarks: '우천취소',
      awayScore: 0,
      homeScore: 0
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
  assert.match(due[0].message, /경기 취소 안내/);
  assert.match(due[0].message, /우천취소 상태입니다/);
  assert.doesNotMatch(due[0].message, /승리|패배|역전은/);
});

test('buildDueAlertDeliveries creates event alert deliveries from score events', () => {
  const selectedDate = new Date(Date.UTC(2026, 4, 5, 0, 0));
  const games = [
    {
      id: '050500',
      time: '14:00',
      away: 'KIA',
      home: 'LG',
      stadium: '잠실',
      remarks: '5회초',
      awayScore: 4,
      homeScore: 3
    }
  ];
  const alerts = [
    {
      discordUserId: 'user-1',
      alertType: ALERT_TYPES.SCORE_CHANGE,
      team: 'KIA',
      notifyBeforeMinutes: 10
    }
  ];
  const events = [
    {
      eventKey: '2026-05-05:050500:score_change:KIA:4-3',
      alertType: ALERT_TYPES.SCORE_CHANGE,
      team: 'KIA',
      gameId: '050500',
      time: '14:00',
      away: 'KIA',
      home: 'LG',
      stadium: '잠실',
      remarks: '5회초',
      awayScore: 4,
      homeScore: 3,
      scoreDelta: 3
    }
  ];

  const due = buildDueAlertDeliveries(alerts, games, selectedDate, { events });

  assert.equal(due.length, 1);
  assert.equal(
    due[0].deliveryKey,
    'user-1:score_change:2026-05-05:050500:score_change:KIA:4-3'
  );
  assert.match(due[0].message, /득점/);
  assert.match(due[0].message, /\+3/);
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

test('runAlertCheck sends score event alerts from previous score snapshots', async (t) => {
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
          remarks: '5회초',
          awayScore: 4,
          homeScore: 3
        }
      ];
    },
    async selectScoreSnapshots(dateKey) {
      events.push(`snapshots:${dateKey}`);
      return [
        {
          snapshotKey: '2026-05-05:050500',
          gameDate: '2026-05-05',
          gameId: '050500',
          time: '14:00',
          away: 'KIA',
          home: 'LG',
          stadium: '잠실',
          remarks: '4회말',
          awayScore: 1,
          homeScore: 3,
          leaderTeam: 'LG'
        }
      ];
    },
    async upsertScoreSnapshots(snapshots) {
      events.push(`upsert:${snapshots.map((snapshot) => snapshot.snapshotKey).join(',')}`);
    },
    async selectEnabledUserAlerts() {
      return [
        {
          discordUserId: 'user-1',
          alertType: ALERT_TYPES.SCORE_CHANGE,
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
            events.push(`dm:${message.includes('+3')}`);
          }
        };
      }
    }
  };

  const result = await runAlertCheck({ client, database, crawler }, {
    now: new Date(Date.UTC(2026, 4, 5, 14, 5)),
    selectedDate,
    selectedDateKey: '0505'
  });

  assert.equal(result.sent, 1);
  assert.equal(events.includes('snapshots:0505'), true);
  assert.equal(events.includes('upsert:2026-05-05:050500'), true);
  assert.equal(
    events.includes('claim:user-1:score_change:2026-05-05:050500:score_change:KIA:4-3'),
    true
  );
  assert.equal(events.includes('dm:true'), true);
});

test('runAlertCheck stores score and lead-change events and uses lead changes in result summaries', async (t) => {
  t.mock.method(console, 'log', () => {});
  const events = [];
  const storedEvents = [];
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
          remarks: '경기종료',
          awayScore: 4,
          homeScore: 3
        }
      ];
    },
    async selectScoreSnapshots(dateKey) {
      events.push(`snapshots:${dateKey}`);
      return [
        {
          snapshotKey: '2026-05-05:050500',
          gameDate: '2026-05-05',
          gameId: '050500',
          time: '14:00',
          away: 'KIA',
          home: 'LG',
          stadium: '잠실',
          remarks: '8회말',
          awayScore: 2,
          homeScore: 3,
          leaderTeam: 'LG'
        }
      ];
    },
    async insertGameEvent(event) {
      events.push(`event:${event.eventKey}`);
      storedEvents.push(event);
      return true;
    },
    async selectGameEventsByGameIds(gameDate, gameIds, eventType) {
      events.push(`history:${gameDate}:${gameIds.join(',')}:${eventType}`);
      return storedEvents.filter((event) => event.alertType === eventType);
    },
    async upsertScoreSnapshots(snapshots) {
      events.push(`upsert:${snapshots.map((snapshot) => snapshot.snapshotKey).join(',')}`);
    },
    async selectEnabledUserAlerts() {
      return [
        {
          discordUserId: 'user-1',
          alertType: ALERT_TYPES.GAME_RESULT,
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
            events.push(`dm:${message.includes('역전은 1번 있었습니다')}:${message.includes('KIA가 4-3으로 앞선 장면')}`);
          }
        };
      }
    }
  };

  const result = await runAlertCheck({ client, database, crawler }, {
    now: new Date(Date.UTC(2026, 4, 5, 17, 0)),
    selectedDate,
    selectedDateKey: '0505'
  });

  assert.equal(result.sent, 1);
  assert.equal(events.includes('snapshots:0505'), true);
  assert.equal(events.includes('event:2026-05-05:050500:score_change:KIA:4-3'), true);
  assert.equal(events.includes('event:2026-05-05:050500:lead_change:KIA:4-3'), true);
  assert.equal(storedEvents.find((event) => event.alertType === ALERT_TYPES.SCORE_CHANGE)?.scoreDelta, 2);
  assert.equal(events.includes('history:2026-05-05:050500:lead_change'), true);
  assert.equal(events.includes('dm:true:true'), true);
});

test('runAlertCheck keeps result summary delivery when lead-change history lookup fails', async (t) => {
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
          remarks: '경기종료',
          awayScore: 4,
          homeScore: 3
        }
      ];
    },
    async selectScoreSnapshots() {
      return [];
    },
    async selectGameEventsByGameIds() {
      events.push('history:failed');
      throw new Error('db down');
    },
    async selectEnabledUserAlerts() {
      return [
        {
          discordUserId: 'user-1',
          alertType: ALERT_TYPES.GAME_RESULT,
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
            events.push(`dm:${message.includes('경기 종료 요약')}:${!message.includes('역전은')}`);
          }
        };
      }
    }
  };

  const result = await runAlertCheck({ client, database, crawler }, {
    now: new Date(Date.UTC(2026, 4, 5, 17, 0)),
    selectedDate,
    selectedDateKey: '0505'
  });

  assert.equal(result.sent, 1);
  assert.equal(events.includes('history:failed'), true);
  assert.equal(events.includes('dm:true:true'), true);
});

test('runAlertCheck keeps result summary delivery when lead-change event storage fails', async (t) => {
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
          remarks: '경기종료',
          awayScore: 4,
          homeScore: 3
        }
      ];
    },
    async selectScoreSnapshots() {
      return [
        {
          snapshotKey: '2026-05-05:050500',
          gameDate: '2026-05-05',
          gameId: '050500',
          time: '14:00',
          away: 'KIA',
          home: 'LG',
          stadium: '잠실',
          remarks: '8회말',
          awayScore: 2,
          homeScore: 3,
          leaderTeam: 'LG'
        }
      ];
    },
    async insertGameEvent() {
      events.push('event:failed');
      throw new Error('insert failed');
    },
    async selectGameEventsByGameIds() {
      return [];
    },
    async selectEnabledUserAlerts() {
      return [
        {
          discordUserId: 'user-1',
          alertType: ALERT_TYPES.GAME_RESULT,
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
            events.push(`dm:${message.includes('경기 종료 요약')}:${!message.includes('역전은')}`);
          }
        };
      }
    }
  };

  const result = await runAlertCheck({ client, database, crawler }, {
    now: new Date(Date.UTC(2026, 4, 5, 17, 0)),
    selectedDate,
    selectedDateKey: '0505'
  });

  assert.equal(result.sent, 1);
  assert.equal(events.includes('event:failed'), true);
  assert.equal(events.includes('dm:true:true'), true);
});
