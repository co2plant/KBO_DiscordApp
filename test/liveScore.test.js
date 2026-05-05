import assert from 'node:assert/strict';
import test from 'node:test';

import {
  liveGameStatus,
  parseScoreboardGames,
  parseScoreValue
} from '../src/services/liveScore.js';

test('parseScoreboardGames extracts game id, teams, scores, status, place, and time', () => {
  const html = `
    <div class="smsScore">
      <div class='score_wrap'>
        <p class='leftTeam'>
          <strong class='teamT'>NC</strong>
          <em class="score"><span>10</span></em>
        </p>
        <strong class="flag"><span>경기종료</span></strong>
        <p class='rightTeam'>
          <em class="score"><span>3</span></em>
          <strong class='teamT'>LG</strong>
        </p>
      </div>
      <div class="btnSms">
        <a href='/Schedule/GameCenter/Main.aspx?gameDate=20260503&gameId=20260503NCLG0&section=REVIEW'>리뷰</a>
      </div>
      <p class="place">잠실 <span>14:00</span></p>
    </div>
  `;

  assert.deepEqual(parseScoreboardGames(html), [
    {
      gameDate: '20260503',
      gameId: '20260503NCLG0',
      awayTeam: 'NC',
      homeTeam: 'LG',
      awayScore: 10,
      homeScore: 3,
      status: '경기종료',
      stadium: '잠실',
      time: '14:00'
    }
  ]);
});

test('liveGameStatus prefers official live state over scoreboard fallback', () => {
  assert.equal(liveGameStatus({ SECTION_ID: 3 }, '9회말'), '경기종료');
  assert.equal(liveGameStatus({ SECTION_ID: 1 }, '-'), '경기전');
  assert.equal(liveGameStatus({ SECTION_ID: 2, INN_NO: 8, TB_NM: '초' }, '-'), '8회초');
  assert.equal(liveGameStatus(null, '우천취소'), '우천취소');
});

test('parseScoreValue normalizes blank scores to sentinel', () => {
  assert.equal(parseScoreValue('10'), 10);
  assert.equal(parseScoreValue(''), -1);
  assert.equal(parseScoreValue(undefined), -1);
});
