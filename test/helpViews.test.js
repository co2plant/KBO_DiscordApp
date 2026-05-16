import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildHelpFields,
  buildHelpIntro
} from '../src/utils/helpViews.js';

test('buildHelpIntro explains how to start with the bot', () => {
  const intro = buildHelpIntro();

  assert.match(intro, /처음이면/);
  assert.match(intro, /\/일정 date:오늘/);
  assert.match(intro, /\/내팀설정 team:KIA/);
});

test('buildHelpFields groups schedule, team, player, and alert commands', () => {
  const fields = buildHelpFields();
  const names = fields.map((field) => field.name);
  const values = fields.map((field) => field.value).join('\n');

  assert.deepEqual(names, ['경기 보기', '팀/선수 보기', '개인 알림', '관리 팁']);
  assert.match(values, /\/경기요약 team:KIA/);
  assert.match(values, /\/내팀설정 team:KIA/);
  assert.match(values, /\/알림설정 team:KIA type:득점/);
  assert.match(values, /\/내알림/);
});
