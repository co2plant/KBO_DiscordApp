export function buildHelpIntro() {
  return [
    '처음이면 `/일정 date:오늘`로 오늘 경기부터 확인하세요.',
    '`/내팀설정 team:KIA`를 먼저 해두면 팀 입력을 자주 생략할 수 있습니다.',
    '실시간 알림은 `/알림설정`으로 팀과 알림 종류를 골라 개인 DM으로 받을 수 있습니다.'
  ].join('\n');
}

export function buildHelpFields() {
  return [
    {
      name: '경기 보기',
      value: [
        '`/일정 date:오늘` 오늘 경기와 실시간 점수',
        '`/경기요약 team:KIA` 오늘 해당 팀 경기 요약',
        '`/팀 team:KIA` 오늘 경기와 팀 성적 요약',
        '`/내팀설정 team:KIA` 기본 팀 저장'
      ].join('\n'),
      inline: false
    },
    {
      name: '팀/선수 보기',
      value: [
        '`/순위` KBO 전체 순위',
        '`/성적 team:KIA` 팀 상세 성적',
        '`/선수 name:홍창기 team:LG` 선수 기본 정보와 시즌 기록'
      ].join('\n'),
      inline: false
    },
    {
      name: '개인 알림',
      value: [
        '`/알림설정 team:KIA type:경기 시작 minutes:10` 경기 시작 전 DM',
        '`/알림설정 team:KIA type:득점` 득점 이벤트 DM',
        '`/알림설정 team:KIA type:역전` 역전 이벤트 DM',
        '`/알림설정 team:KIA type:경기 취소` 취소 이벤트 DM',
        '`/알림해제 team:KIA type:득점` 알림 해제',
        '`/내알림` 내 구독 목록 확인'
      ].join('\n'),
      inline: false
    },
    {
      name: '관리 팁',
      value: [
        '점수, 이벤트 알림, 경기 요약은 오늘 경기 데이터를 기준으로 갱신됩니다.',
        '개인 알림은 서버 채널이 아니라 본인 DM으로 발송됩니다.'
      ].join('\n'),
      inline: false
    }
  ];
}
