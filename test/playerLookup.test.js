import assert from 'node:assert/strict';
import test from 'node:test';

import {
  getPlayerById,
  resolvePlayerLookup
} from '../src/services/playerLookup.js';

function createFakeDatabase(players = []) {
  const stored = new Map(players.map((player) => [player.playerId, player]));
  return {
    stored,
    async selectPlayersByName(name) {
      return [...stored.values()].filter((player) => player.name === name);
    },
    async selectPlayerByNameAndTeam(name, team) {
      return [...stored.values()].find((player) => player.name === name && player.team === team) ?? null;
    },
    async selectPlayerById(playerId) {
      return stored.get(playerId) ?? null;
    },
    async upsertPlayer(player) {
      stored.set(player.playerId, player);
    }
  };
}

test('resolvePlayerLookup returns cached player without crawling when team narrows the search', async (t) => {
  t.mock.method(console, 'log', () => {});
  const cached = { playerId: '66108', name: '홍창기', team: 'LG' };
  const database = createFakeDatabase([cached]);
  let crawled = false;
  const crawler = {
    async searchPlayers() {
      crawled = true;
      return [];
    }
  };

  const result = await resolvePlayerLookup({ name: '홍창기', team: 'LG' }, database, crawler);

  assert.deepEqual(result, { type: 'player', player: cached, source: 'cache' });
  assert.equal(crawled, false);
});

test('resolvePlayerLookup returns candidates when KBO search has same-name players', async () => {
  const database = createFakeDatabase();
  const candidates = [
    { playerId: '66108', name: '홍창기', team: 'LG', position: '외야수' },
    { playerId: '50001', name: '홍창기', team: '삼성', position: '투수' }
  ];
  const crawler = {
    async searchPlayers(keyword) {
      assert.equal(keyword, '홍창기');
      return candidates;
    }
  };

  const result = await resolvePlayerLookup({ name: '홍창기' }, database, crawler);

  assert.deepEqual(result, { type: 'candidates', candidates, source: 'network' });
});

test('getPlayerById fetches detail and stores it when cache misses', async () => {
  const database = createFakeDatabase();
  const detail = {
    playerId: '66108',
    name: '홍창기',
    team: 'LG',
    detailUrl: 'https://www.koreabaseball.com/Record/Player/HitterDetail/Basic.aspx?playerId=66108'
  };
  const crawler = {
    async fetchPlayerDetail(candidate) {
      assert.equal(candidate.playerId, '66108');
      return detail;
    }
  };

  const player = await getPlayerById('66108', database, crawler, {
    playerId: '66108',
    detailUrl: detail.detailUrl
  });

  assert.deepEqual(player, detail);
  assert.deepEqual(database.stored.get('66108'), detail);
});
