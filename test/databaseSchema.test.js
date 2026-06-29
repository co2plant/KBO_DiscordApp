import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

test('database schema includes score snapshots for live event detection', () => {
  const source = readFileSync('src/services/database.js', 'utf8');

  assert.match(source, /CREATE TABLE IF NOT EXISTS ScoreSnapshots/);
  assert.match(source, /export async function selectScoreSnapshots/);
  assert.match(source, /export async function upsertScoreSnapshots/);
});

test('database schema includes game events for lead-change result summaries', () => {
  const source = readFileSync('src/services/database.js', 'utf8');

  assert.match(source, /CREATE TABLE IF NOT EXISTS GameEvents/);
  assert.match(source, /event_key VARCHAR\(128\) PRIMARY KEY/);
  assert.match(source, /idx_game_events_game/);
  assert.match(source, /export async function insertGameEvent/);
  assert.match(source, /export async function selectGameEventsByGameIds/);
});

test('database schema includes user preferences for default team settings', () => {
  const source = readFileSync('src/services/database.js', 'utf8');

  assert.match(source, /CREATE TABLE IF NOT EXISTS UserPreferences/);
  assert.match(source, /export async function upsertUserPreference/);
  assert.match(source, /export async function selectUserPreference/);
  assert.match(source, /export async function deleteUserPreference/);
});

test('database exposes player autocomplete lookup for slash command suggestions', () => {
  const source = readFileSync('src/services/database.js', 'utf8');

  assert.match(source, /export async function selectPlayerAutocomplete/);
  assert.match(source, /GROUP_CONCAT\(DISTINCT team/);
});

test('database schema includes command logs for production usage audit', () => {
  const source = readFileSync('src/services/database.js', 'utf8');

  assert.match(source, /CREATE TABLE IF NOT EXISTS CommandLogs/);
  assert.match(source, /export async function insertCommandLog/);
  assert.match(source, /interaction_id VARCHAR\(32\) NOT NULL UNIQUE/);
  assert.match(source, /duration_ms INT NOT NULL/);
});
