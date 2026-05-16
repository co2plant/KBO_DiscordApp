import assert from 'node:assert/strict';
import test from 'node:test';

import { buildGameSummary } from '../src/services/gameSummary.js';

test('buildGameSummary explains a final game result from the requested team view', () => {
  const selectedDate = new Date(Date.UTC(2026, 4, 5, 0, 0));
  const summary = buildGameSummary({
    id: '050500',
    time: '14:00',
    away: 'KIA',
    home: 'LG',
    stadium: '잠실',
    remarks: '경기종료',
    awayScore: 5,
    homeScore: 3
  }, 'KIA', selectedDate);

  assert.equal(summary.title, 'KIA 경기 요약');
  assert.match(summary.scoreLine, /KIA 5 vs 3 .*LG/);
  assert.match(summary.summary, /KIA가 2점 차로 승리/);
});

test('buildGameSummary explains a live tied game', () => {
  const selectedDate = new Date(Date.UTC(2026, 4, 5, 0, 0));
  const summary = buildGameSummary({
    id: '050501',
    time: '14:00',
    away: 'KIA',
    home: 'LG',
    stadium: '잠실',
    remarks: '5회말',
    awayScore: 4,
    homeScore: 4
  }, 'LG', selectedDate);

  assert.match(summary.summary, /동점/);
  assert.match(summary.context, /5회말/);
});

test('buildGameSummary explains cancelled games without inventing a winner', () => {
  const selectedDate = new Date(Date.UTC(2026, 4, 5, 0, 0));
  const summary = buildGameSummary({
    id: '050502',
    time: '18:30',
    away: 'KIA',
    home: 'LG',
    stadium: '잠실',
    remarks: '우천취소',
    awayScore: 0,
    homeScore: 0
  }, 'KIA', selectedDate);

  assert.match(summary.summary, /취소/);
  assert.doesNotMatch(summary.summary, /승리/);
});
