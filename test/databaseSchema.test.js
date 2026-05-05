import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

test('database schema includes score snapshots for live event detection', () => {
  const source = readFileSync('src/services/database.js', 'utf8');

  assert.match(source, /CREATE TABLE IF NOT EXISTS ScoreSnapshots/);
  assert.match(source, /export async function selectScoreSnapshots/);
  assert.match(source, /export async function upsertScoreSnapshots/);
});
