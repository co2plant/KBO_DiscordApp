import assert from 'node:assert/strict';
import test from 'node:test';

import {
  parsePlayerDetail,
  parsePlayerSearchResults
} from '../src/services/playerCrawler.js';

test('parsePlayerSearchResults extracts player candidates from KBO search table', () => {
  const html = `
    <table class="tEx">
      <tbody>
        <tr>
          <td>51</td>
          <td><a href='/Record/Player/HitterDetail/Basic.aspx?playerId=66108'>홍창기</a></td>
          <td>LG</td>
          <td>외야수</td>
          <td>1993-11-21</td>
          <td>189cm, 94kg</td>
          <td>대일초-매송중-안산공고-건국대-LG-경찰</td>
        </tr>
        <tr>
          <td>15</td>
          <td><a href="/Record/Player/PitcherDetail/Basic.aspx?playerId=50001">홍창기</a></td>
          <td>삼성</td>
          <td>투수</td>
          <td>2001-02-03</td>
          <td>184cm, 86kg</td>
          <td>대구초-경북중-경북고</td>
        </tr>
      </tbody>
    </table>
  `;

  assert.deepEqual(parsePlayerSearchResults(html), [
    {
      playerId: '66108',
      name: '홍창기',
      team: 'LG',
      backNo: '51',
      position: '외야수',
      birthday: '1993-11-21',
      heightWeight: '189cm, 94kg',
      career: '대일초-매송중-안산공고-건국대-LG-경찰',
      detailUrl: 'https://www.koreabaseball.com/Record/Player/HitterDetail/Basic.aspx?playerId=66108',
      detailType: 'hitter'
    },
    {
      playerId: '50001',
      name: '홍창기',
      team: '삼성',
      backNo: '15',
      position: '투수',
      birthday: '2001-02-03',
      heightWeight: '184cm, 86kg',
      career: '대구초-경북중-경북고',
      detailUrl: 'https://www.koreabaseball.com/Record/Player/PitcherDetail/Basic.aspx?playerId=50001',
      detailType: 'pitcher'
    }
  ]);
});

test('parsePlayerDetail extracts basic profile from KBO player detail page', () => {
  const html = `
    <div class="player_info">
      <h4 id="h4Team" class="team regular/2026/emblem_LG">
        <span class='emb'><img src='//6ptotvmi5753.edge.naverncp.com/KBO_IMAGE/emblem/regular/2026/emblem_LG.png' /></span>LG 트윈스
      </h4>
      <div class="player_basic">
        <div class="photo"><img id="cphContents_cphContents_cphContents_playerProfile_imgProgile" src="//6ptotvmi5753.edge.naverncp.com/KBO_IMAGE/person/middle/2026/66108.jpg" alt="홍창기" /></div>
        <ul>
          <li class="odd"><strong>선수명: </strong><span id="cphContents_cphContents_cphContents_playerProfile_lblName">홍창기</span></li>
          <li><strong>등번호: </strong>No.<span id="cphContents_cphContents_cphContents_playerProfile_lblBackNo">51</span></li>
          <li class="odd"><strong>생년월일: </strong><span id="cphContents_cphContents_cphContents_playerProfile_lblBirthday">1993년 11월 21일</span></li>
          <li><strong>포지션: </strong><span id="cphContents_cphContents_cphContents_playerProfile_lblPosition">외야수(우투좌타)</span></li>
          <li class="odd"><strong>신장/체중: </strong><span id="cphContents_cphContents_cphContents_playerProfile_lblHeightWeight">189cm/94kg</span></li>
          <li><strong>경력: </strong><span id="cphContents_cphContents_cphContents_playerProfile_lblCareer">대일초-매송중-안산공고-건국대-LG-경찰</span></li>
          <li class="odd"><strong>입단 계약금: </strong><span id="cphContents_cphContents_cphContents_playerProfile_lblPayment">8000만원</span></li>
          <li><strong>연봉: </strong><span id="cphContents_cphContents_cphContents_playerProfile_lblSalary">52000만원</span></li>
          <li class="odd"><strong>지명순위: </strong><span id="cphContents_cphContents_cphContents_playerProfile_lblDraft">16 LG 2차 3라운드 27순위</span></li>
          <li><strong>입단년도: </strong><span id="cphContents_cphContents_cphContents_playerProfile_lblJoinInfo">16LG</span></li>
        </ul>
      </div>
    </div>
  `;

  assert.deepEqual(parsePlayerDetail(html, {
    playerId: '66108',
    detailUrl: 'https://www.koreabaseball.com/Record/Player/HitterDetail/Basic.aspx?playerId=66108',
    detailType: 'hitter'
  }), {
    playerId: '66108',
    detailUrl: 'https://www.koreabaseball.com/Record/Player/HitterDetail/Basic.aspx?playerId=66108',
    detailType: 'hitter',
    team: 'LG',
    teamName: 'LG 트윈스',
    name: '홍창기',
    backNo: '51',
    birthday: '1993년 11월 21일',
    position: '외야수(우투좌타)',
    heightWeight: '189cm/94kg',
    career: '대일초-매송중-안산공고-건국대-LG-경찰',
    payment: '8000만원',
    salary: '52000만원',
    draft: '16 LG 2차 3라운드 27순위',
    joinInfo: '16LG',
    profileImageUrl: 'https://6ptotvmi5753.edge.naverncp.com/KBO_IMAGE/person/middle/2026/66108.jpg'
  });
});
