import assert from 'node:assert/strict';
import test from 'node:test';

import {
  handlePlayerComponent,
  isPlayerComponent
} from '../src/interactions/playerInteractions.js';

test('isPlayerComponent matches player buttons and select menus', () => {
  assert.equal(isPlayerComponent({
    isButton: () => true,
    isStringSelectMenu: () => false,
    customId: 'kbo_player:button:1234:66108:hitter'
  }), true);
  assert.equal(isPlayerComponent({
    isButton: () => false,
    isStringSelectMenu: () => false,
    customId: 'kbo_player:button:1234:66108:hitter'
  }), false);
});

test('handlePlayerComponent allows only the original requester to choose', async () => {
  let replyPayload;
  const handled = await handlePlayerComponent({
    customId: 'kbo_player:button:owner:66108:hitter',
    values: [],
    user: { id: 'other' },
    async reply(payload) {
      replyPayload = payload;
    }
  }, {});

  assert.equal(handled, true);
  assert.deepEqual(replyPayload, {
    content: '처음 선수 조회를 요청한 사용자만 선택할 수 있습니다.',
    ephemeral: true
  });
});
