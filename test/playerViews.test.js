import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildPlayerCandidateResponse,
  buildPlayerDetailUrl,
  buildPlayerEmbed,
  parsePlayerComponentCustomId
} from '../src/utils/playerViews.js';

const player = {
  playerId: '66108',
  name: '홍창기',
  team: 'LG',
  teamName: 'LG 트윈스',
  backNo: '51',
  birthday: '1993년 11월 21일',
  position: '외야수(우투좌타)',
  heightWeight: '189cm/94kg',
  career: '대일초-매송중-안산공고-건국대-LG-경찰',
  payment: '8000만원',
  salary: '52000만원',
  draft: '16 LG 2차 3라운드 27순위',
  joinInfo: '16LG',
  profileImageUrl: 'https://example.test/66108.jpg',
  detailUrl: 'https://www.koreabaseball.com/Record/Player/HitterDetail/Basic.aspx?playerId=66108',
  detailType: 'hitter'
};

test('buildPlayerEmbed renders player profile fields', () => {
  const embed = buildPlayerEmbed(player);

  assert.equal(embed.title, '<:LG:1242717643966779404> 홍창기 선수 정보');
  assert.equal(embed.url, player.detailUrl);
  assert.equal(embed.thumbnail.url, player.profileImageUrl);
  assert.deepEqual(embed.fields.slice(0, 4), [
    { name: '팀', value: 'LG 트윈스', inline: true },
    { name: '등번호', value: '51', inline: true },
    { name: '포지션', value: '외야수(우투좌타)', inline: true },
    { name: '생년월일', value: '1993년 11월 21일', inline: true }
  ]);
});

test('buildPlayerEmbed renders hitter season stats when present', () => {
  const embed = buildPlayerEmbed({
    ...player,
    seasonStats: {
      year: '2026',
      type: 'hitter',
      stats: {
        AVG: '0.188',
        OPS: '0.656',
        HR: '0',
        RBI: '7',
        SB: '2'
      }
    }
  });

  assert.deepEqual(embed.fields[0], {
    name: '2026 성적',
    value: 'AVG 0.188 · OPS 0.656 · HR 0 · RBI 7 · SB 2',
    inline: false
  });
});

test('buildPlayerEmbed renders pitcher season stats when present', () => {
  const embed = buildPlayerEmbed({
    ...player,
    detailType: 'pitcher',
    seasonStats: {
      year: '2026',
      type: 'pitcher',
      stats: {
        ERA: '3.99',
        W: '2',
        L: '2',
        SV: '0',
        HLD: '0',
        IP: '29 1/3',
        SO: '24',
        WHIP: '1.33'
      }
    }
  });

  assert.deepEqual(embed.fields[0], {
    name: '2026 성적',
    value: 'ERA 3.99 · 2승 2패 · SV 0 · HLD 0 · IP 29 1/3 · SO 24 · WHIP 1.33',
    inline: false
  });
});

test('buildPlayerCandidateResponse uses buttons for five or fewer candidates', () => {
  const response = buildPlayerCandidateResponse([
    player,
    { ...player, playerId: '50001', team: '삼성', position: '투수', detailType: 'pitcher' }
  ], '1234');
  const row = response.components[0];

  assert.equal(response.embeds[0].title, '동명이인 선수 선택');
  assert.equal(row.components.length, 2);
  assert.equal(row.components[0].custom_id, 'kbo_player:button:1234:66108:hitter');
  assert.equal(row.components[1].custom_id, 'kbo_player:button:1234:50001:pitcher');
});

test('buildPlayerCandidateResponse uses select menu for more than five candidates', () => {
  const candidates = Array.from({ length: 6 }, (_, index) => ({
    ...player,
    playerId: `66${index}`,
    team: `팀${index}`,
    detailType: 'hitter'
  }));

  const response = buildPlayerCandidateResponse(candidates, '1234');
  const row = response.components[0];

  assert.equal(row.components[0].custom_id, 'kbo_player:select:1234');
  assert.equal(row.components[0].options.length, 6);
  assert.equal(row.components[0].options[0].value, '660:hitter');
});

test('parsePlayerComponentCustomId reads button and select payloads', () => {
  assert.deepEqual(parsePlayerComponentCustomId('kbo_player:button:1234:66108:hitter'), {
    type: 'button',
    ownerId: '1234',
    playerId: '66108',
    detailType: 'hitter'
  });
  assert.deepEqual(parsePlayerComponentCustomId('kbo_player:select:1234', ['50001:pitcher']), {
    type: 'select',
    ownerId: '1234',
    playerId: '50001',
    detailType: 'pitcher'
  });
  assert.equal(
    buildPlayerDetailUrl('50001', 'pitcher'),
    'https://www.koreabaseball.com/Record/Player/PitcherDetail/Basic.aspx?playerId=50001'
  );
});
