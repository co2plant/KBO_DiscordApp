import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildScoreEvents,
  buildScoreSnapshot
} from '../src/services/scoreEvents.js';
import { ALERT_TYPES } from '../src/services/alerts.js';

test('buildScoreSnapshot uses a year-qualified key and records the current leader', () => {
  const selectedDate = new Date(Date.UTC(2026, 4, 5, 0, 0));
  const snapshot = buildScoreSnapshot({
    id: '050500',
    time: '14:00',
    away: 'KIA',
    home: 'LG',
    stadium: '잠실',
    remarks: '5회초',
    awayScore: 4,
    homeScore: 3
  }, selectedDate);

  assert.equal(snapshot.snapshotKey, '2026-05-05:050500');
  assert.equal(snapshot.leaderTeam, 'KIA');
});

test('buildScoreEvents emits score and lead-change events when the subscribed team takes the lead', () => {
  const selectedDate = new Date(Date.UTC(2026, 4, 5, 0, 0));
  const previous = buildScoreSnapshot({
    id: '050500',
    time: '14:00',
    away: 'KIA',
    home: 'LG',
    stadium: '잠실',
    remarks: '4회말',
    awayScore: 1,
    homeScore: 3
  }, selectedDate);
  const current = {
    id: '050500',
    time: '14:00',
    away: 'KIA',
    home: 'LG',
    stadium: '잠실',
    remarks: '5회초',
    awayScore: 4,
    homeScore: 3
  };

  const events = buildScoreEvents([previous], [current], selectedDate);

  assert.deepEqual(events.map((event) => event.alertType), [
    ALERT_TYPES.SCORE_CHANGE,
    ALERT_TYPES.LEAD_CHANGE
  ]);
  assert.equal(events[0].team, 'KIA');
  assert.equal(events[0].scoreDelta, 3);
  assert.equal(events[0].gameDate, '2026-05-05');
  assert.equal(events[0].eventKey, '2026-05-05:050500:score_change:KIA:4-3');
  assert.equal(events[1].team, 'KIA');
  assert.equal(events[1].previousLeaderTeam, 'LG');
  assert.equal(events[1].gameDate, '2026-05-05');
  assert.equal(events[1].eventKey, '2026-05-05:050500:lead_change:KIA:4-3');
});

test('buildScoreEvents emits cancellation events for both teams when a game is cancelled', () => {
  const selectedDate = new Date(Date.UTC(2026, 4, 5, 0, 0));
  const previous = buildScoreSnapshot({
    id: '050501',
    time: '18:30',
    away: 'KIA',
    home: 'LG',
    stadium: '잠실',
    remarks: '-',
    awayScore: 0,
    homeScore: 0
  }, selectedDate);
  const current = {
    id: '050501',
    time: '18:30',
    away: 'KIA',
    home: 'LG',
    stadium: '잠실',
    remarks: '우천취소',
    awayScore: 0,
    homeScore: 0
  };

  const events = buildScoreEvents([previous], [current], selectedDate);

  assert.deepEqual(events.map((event) => event.alertType), [
    ALERT_TYPES.GAME_CANCELLED,
    ALERT_TYPES.GAME_CANCELLED
  ]);
  assert.deepEqual(events.map((event) => event.team), ['KIA', 'LG']);
  assert.equal(events[0].eventKey, '2026-05-05:050501:game_cancelled:KIA:우천취소');
  assert.equal(events[1].eventKey, '2026-05-05:050501:game_cancelled:LG:우천취소');
});
