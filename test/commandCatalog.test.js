import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

test('command catalog does not expose score command because schedule covers live scores', () => {
  const source = readFileSync('src/commands/kboCommands.js', 'utf8');
  const commandNames = [...source.matchAll(/\.setName\('([^']+)'\)/g)].map((match) => match[1]);

  assert.equal(commandNames.includes('일정'), true);
  assert.equal(commandNames.includes('스코어'), false);
});
