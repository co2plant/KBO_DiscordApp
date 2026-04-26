const assert = require('node:assert/strict');
const test = require('node:test');

process.env.DISCORD_TOKEN = 'test-token';
process.env.DISCORD_CLIENT_ID = '123456789012345678';
process.env.DISCORD_CHANNEL_ID = '123456789012345678';
process.env.DISCORD_GUILD_ID = '123456789012345678';
process.env.DB_USER = 'user';
process.env.DB_PASSWORD = 'password';
process.env.DB_NAME = 'kbo';

const { buildGameId, splitMatchupText } = require('../src/crawler/kboCrawler');

test('splitMatchupText extracts teams and scores', () => {
  const { team, score } = splitMatchupText('한화3vs2LG');

  assert.deepEqual(team, ['한화', 'LG']);
  assert.deepEqual(score, ['3', '2']);
});

test('splitMatchupText preserves empty scores', () => {
  const { team, score } = splitMatchupText('한화vsLG');

  assert.deepEqual(team, ['한화', 'LG']);
  assert.deepEqual(score, ['', '']);
});

test('buildGameId uses two-digit game index', () => {
  assert.equal(buildGameId('0422', 0), '042200');
  assert.equal(buildGameId('0422', 9), '042209');
});
