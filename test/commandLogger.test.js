import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildCommandLogEntry,
  recordCommandLog
} from '../src/services/commandLogger.js';

function fakeInteraction(options = {}) {
  return {
    id: options.id ?? 'interaction-1',
    commandName: options.commandName ?? 'schedule',
    guildId: options.guildId ?? 'guild-1',
    channelId: options.channelId ?? 'channel-1',
    user: {
      id: options.userId ?? 'user-1'
    },
    options: {
      data: options.optionData ?? [
        { name: 'date', value: 'today' },
        { name: 'team', value: 'KIA' }
      ]
    }
  };
}

test('buildCommandLogEntry captures command metadata and sanitized options', () => {
  const entry = buildCommandLogEntry(fakeInteraction(), {
    status: 'success',
    durationMs: 123
  });

  assert.deepEqual(entry, {
    interactionId: 'interaction-1',
    commandName: 'schedule',
    discordUserId: 'user-1',
    guildId: 'guild-1',
    channelId: 'channel-1',
    optionsJson: '{"date":"today","team":"KIA"}',
    status: 'success',
    durationMs: 123,
    errorMessage: ''
  });
});

test('buildCommandLogEntry truncates long error messages and option payloads', () => {
  const entry = buildCommandLogEntry(fakeInteraction({
    optionData: [{ name: 'name', value: 'x'.repeat(3000) }]
  }), {
    status: 'failed',
    durationMs: 5,
    error: new Error('y'.repeat(1000))
  });

  assert.equal(entry.optionsJson.length <= 2048, true);
  assert.equal(JSON.parse(entry.optionsJson)._truncated, true);
  assert.equal(entry.errorMessage.length, 512);
});

test('recordCommandLog writes the entry and never throws when logging fails', async (t) => {
  t.mock.method(console, 'log', () => {});
  const entries = [];
  const successDatabase = {
    async insertCommandLog(entry) {
      entries.push(entry);
    }
  };

  await recordCommandLog(successDatabase, fakeInteraction(), {
    status: 'success',
    durationMs: 10
  });

  assert.equal(entries.length, 1);
  assert.equal(entries[0].commandName, 'schedule');

  const failingDatabase = {
    async insertCommandLog() {
      throw new Error('db down');
    }
  };

  await recordCommandLog(failingDatabase, fakeInteraction(), {
    status: 'failed',
    durationMs: 10
  });
});
