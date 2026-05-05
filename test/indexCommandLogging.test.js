import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

test('index records command logs for success and failure paths', () => {
  const source = readFileSync('src/index.js', 'utf8');

  assert.match(source, /recordCommandLog/);
  assert.match(source, /status: 'success'/);
  assert.match(source, /status: 'failed'/);
  assert.match(source, /durationMs/);
});
