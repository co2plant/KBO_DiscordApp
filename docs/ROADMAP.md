# KBO Discord Bot Roadmap

작성일: 2026-05-17

이 문서는 KBO_DiscordApp의 기준 개발 문서입니다. 새 기능이나 구조 변경은 이 로드맵에서 작업 후보를 고른 뒤, Spec과 Plan을 확정하고 구현합니다.

## 목적

KBO 팬이 Discord 안에서 경기 일정, 실시간 경기 흐름, 순위, 선수 정보, 응원팀 알림을 빠르게 확인할 수 있는 봇을 운영합니다. 핵심 가치는 "지금 경기 어떻게 됐어?"라는 질문에 짧고 신뢰 가능한 흐름으로 답하는 것입니다.

## 현재 기준

- 런타임: Node.js, discord.js v14, ESM
- 저장소: MariaDB, `mysql2/promise`
- 크롤링: KBO 웹 페이지, `puppeteer-core`, KBO 모바일 live state API
- 실행: Docker Compose, `node:22-slim`, Chromium 포함
- 검증: Node built-in test runner, GitHub Actions CI
- 운영 서버 리소스: 1 vCPU, 1GB RAM 기준으로 설계
- 운영 원칙: polling, Chromium 실행, DB 쿼리, Docker 재시작 비용을 낮게 유지

## 운영 제약과 장애 대응 원칙

- 서버 리소스가 작으므로 기능 추가 시 상시 CPU/RAM 사용량을 늘리는 설계는 피합니다.
- 알림 worker는 기존 polling 주기를 우선 재사용하고, 새 interval이나 background loop를 추가하지 않습니다.
- KBO 페이지 크롤링은 필요한 시점에만 수행하고, 가능하면 기존 schedule/live score 갱신 결과를 재사용합니다.
- DB에는 종료 요약에 필요한 최소 이벤트만 저장합니다. 이번 자동 요약 기능은 `lead_change`만 저장하고 전체 득점 타임라인은 저장하지 않습니다.
- 장애가 발생해도 봇 프로세스가 죽지 않아야 합니다. 개별 알림 생성, 이벤트 저장, DM 발송 실패는 로그를 남기고 다음 사용자/다음 경기 처리를 계속합니다.
- DB 저장 실패 시 종료 요약 DM은 최종 스코어와 승패만으로 fallback합니다. 역전 문장은 생략합니다.
- 봇 재시작이나 경기 중 장애로 이벤트 히스토리가 비어 있으면 과거 흐름을 추정하지 않습니다. 최종 스코어와 승패만 보냅니다.
- KBO 응답 실패나 timeout이 발생하면 기존 저장 데이터를 사용하고, 없는 데이터는 억지로 추정하지 않습니다.
- 중복 DM은 기존 delivery key 정책으로 방지합니다.
- CI는 GitHub runner에서 syntax check, test, Docker build를 수행합니다. 운영 서버의 1 vCPU/1GB RAM에서 Docker image build를 수행하는 배포 방식은 피합니다.
- CD를 추가할 경우 운영 서버에서는 가벼운 restart-only 배포만 수행합니다. 서버에서 test, Docker build, 일반 build 작업을 실행하지 않습니다.
- 의존성 재현성을 위해 `package-lock.json`을 저장소에 포함합니다. lockfile이 생기면 CI는 `npm install`이 아니라 `npm ci`를 사용합니다.
- 운영 서버에서는 `package.json` 또는 `package-lock.json`이 바뀐 배포에서만 `npm install --omit=dev`를 실행합니다.

## 작업 상태값

- `Backlog`: 후보로 남아 있지만 아직 Spec이 없습니다.
- `Spec`: 목표, 범위, 제외 범위, 완료 기준을 작성 중입니다.
- `Plan`: 구현 단계, 영향 범위, 검증 방법을 작성 중입니다.
- `Ready`: Spec과 Plan이 확정되어 구현할 수 있습니다.
- `In Progress`: 현재 구현 중입니다.
- `Done`: 구현과 검증이 완료되었습니다.
- `Archived`: 현재 기준과 맞지 않아 참고용으로만 남깁니다.

## 완료된 기능

상태: `Done`

- Discord slash command 런타임 전환
  - `/순위`, `/성적`, `/일정`, `/팀`, `/경기요약`
  - `/선수`
  - `/도움말`
  - `/내팀설정`, `/내팀`, `/내팀해제`
  - `/알림설정`, `/알림해제`, `/내알림`
  - `/차렷`, `/열중쉬어`, `/쉬어`
- 데이터 준비와 갱신
  - 봇 시작 시 standings와 당일 schedule bootstrap
  - 명령 실행 시 standings refresh
  - 당일 경기 live window에서 live score refresh
- 개인화
  - 사용자별 기본 팀 저장
  - 팀 입력 autocomplete
  - 선수 이름 autocomplete
- 알림
  - 개인 DM 경기 시작 알림
  - 경기 종료 알림
  - 득점, 역전, 경기 취소 이벤트 알림
  - 중복 발송 방지용 delivery 기록
- 운영/검증
  - Docker Compose 실행
  - GitHub Actions CI
  - Docker 없는 systemd 운영 기준 문서
  - 명령 실행 로그 저장
  - 주요 parser, formatter, command, alert, database schema 테스트

## 로드맵

### Phase 1: 운영 문서와 개발 절차 안정화

상태: `Ready`

목표: 새 기능을 시작하기 전에 문서 기준, 작업 절차, 검증 기준을 일관되게 만듭니다.

작업 후보:
- README 명령 목록과 실제 slash command 목록 동기화
- 개발 절차를 `PLAN_FIRST_WORKFLOW.md`에 명확히 정리
- 오래된 `docs/superpowers/*` 문서를 canonical 로드맵 기준으로 정리
- CI 실행 결과와 로컬 검증 명령을 운영 문서에 반영

완료 기준:
- 새 작업자는 `docs/ROADMAP.md`와 `PLAN_FIRST_WORKFLOW.md`만 보고 다음 작업을 시작할 수 있습니다.
- 오래된 JS 전환 문서가 현재 상태를 미완료로 오해하게 만들지 않습니다.

### Phase 2: 서버별 운영 설정

상태: `Backlog`

목표: 개인 DM 중심 알림에서 서버 운영자 중심 설정으로 확장합니다.

작업 후보:
- 서버별 기본 응원팀 설정
- 서버별 알림 채널 설정
- 서버별 알림 on/off
- 관리자 권한 검증과 실패 메시지 정리

완료 기준:
- 설정이 서버 단위로 영속 저장됩니다.
- 설정이 없는 서버에서도 기존 조회 명령은 정상 동작합니다.
- 권한 부족, 채널 접근 실패, Discord API 실패가 사용자에게 명확히 안내됩니다.

### Phase 3: 경기 전후 자동 요약

상태: `Spec`

목표: 사용자가 직접 명령을 호출하지 않아도 주요 경기 흐름을 받을 수 있게 합니다.

작업 후보:
- 경기 시작 전 라인업 또는 선발 정보 알림
- 경기 종료 후 자동 요약
- 최종 점수, 승패, 주요 이벤트 포함
- 개인 알림과 서버 채널 알림의 중복 정책 정리

완료 기준:
- 같은 이벤트가 반복 발송되지 않습니다.
- 경기 취소, 지연, 데이터 수집 실패 상황을 구분합니다.
- 수집 실패 시 기존 저장 데이터로 가능한 범위에서 응답합니다.

#### 확정 Spec: 경기 종료 후 개인 DM 자동 요약

상태: `Spec`

Goal 입력용 요약:

> 기존 `/알림설정`의 `경기 종료` 알림을 단순 종료 알림에서 경기 종료 자동 요약 DM으로 개선한다. 요약은 최종 스코어, 구독 팀 기준 승패, 역전 횟수, 마지막 역전 장면을 짧은 중립형 문장으로 전달한다. 역전 흐름은 경기 중 감지한 `lead_change` 이벤트만 DB에 저장해 종료 시점에 사용한다.

목표:
- 경기 종료 알림을 받은 사용자가 별도 명령을 실행하지 않아도 최종 결과와 핵심 역전 흐름을 알 수 있게 합니다.
- 기존 개인 DM 알림 구조를 재사용해 서버 채널 설정 없이 먼저 사용자 가치를 제공합니다.
- 일반 득점 전체가 아니라 `lead_change`만 저장해 구현 범위와 메시지 길이를 제한합니다.
- 1 vCPU, 1GB RAM 운영 서버에서 안정적으로 돌도록 새 background loop나 무거운 크롤링을 추가하지 않습니다.

대상 사용자:
- `/알림설정`에서 특정 팀의 `경기 종료` 알림을 켠 사용자
- 구독 팀의 경기 종료 후 DM으로 결과 요약을 받고 싶은 사용자

현재 동작:
- 알림 워커가 경기 종료 상태를 감지하면 `GAME_RESULT` 구독자에게 개인 DM을 보냅니다.
- 현재 메시지는 경기 종료 알림, 최종 스코어, 경기 시간/구장/상태 중심의 단순 텍스트입니다.
- 점수 스냅샷은 저장하지만, 경기 중 역전 이벤트 히스토리는 영속 저장하지 않습니다.

변경 후 동작:
- `GAME_RESULT` DM은 경기 종료 요약 메시지로 대체합니다.
- 경기 중 알림 워커가 점수 스냅샷을 비교할 때 리드 팀 변경을 감지하면 `lead_change` 이벤트를 저장합니다.
- 경기 종료 DM 생성 시 해당 경기의 저장된 `lead_change` 이벤트를 조회해 역전 횟수와 마지막 역전 장면을 포함합니다.
- 구독 팀이 승리, 패배, 무승부 중 어느 결과인지 구독 팀 기준으로 표현합니다.
- 취소 경기는 승패/역전 문장을 만들지 않고 취소 안내 중심으로 보냅니다.
- 이벤트 저장이나 이벤트 조회가 실패하면 최종 스코어와 승패만 포함한 종료 요약을 보냅니다.

포함 범위:
- 개인 DM 경기 종료 요약
- `lead_change` 이벤트 히스토리 저장
- 역전 횟수 계산
- 마지막 역전 장면 표시
- 취소 경기 안내
- 기존 중복 발송 방지 정책 유지

제외 범위:
- 서버 채널 자동 요약 발송
- 새 slash command 추가
- 전체 득점 이벤트 저장
- 동점 이벤트 표시
- 라인업, 투수, 선수별 활약, 뉴스 기반 요약
- LLM 기반 자연어 요약
- 새 polling worker 추가
- 운영 서버에서 Docker image build를 수행하는 CD 구성

역전 판정 규칙:
- 리드 팀이 없던 상태에서 한 팀이 앞서기 시작한 장면은 `lead_change`로 저장하지 않습니다.
- 이전 리드 팀과 현재 리드 팀이 모두 있고 서로 다를 때만 `lead_change`로 저장합니다.
- 동점 상태 자체는 종료 요약에 표시하지 않습니다.
- `A 리드 -> 동점 -> B 리드` 흐름은 B가 리드를 잡은 시점에 `lead_change` 1회로 봅니다.
- 동일 경기, 동일 스코어, 동일 리드 팀 이벤트는 중복 저장하지 않습니다.

이벤트 저장 규칙:
- 저장 이벤트 타입은 `lead_change`만 사용합니다.
- 이벤트는 경기 단위로 조회 가능해야 합니다.
- 동일 이벤트 저장은 idempotent해야 하며, 중복 key 충돌은 실패가 아니라 이미 저장된 상태로 처리합니다.
- 이벤트 저장 실패는 알림 worker 전체 실패로 전파하지 않습니다.
- 이벤트에는 최소한 다음 정보가 있어야 합니다.
  - event key
  - game date
  - game id
  - event type
  - inning/status text
  - team that took the lead
  - previous leader team
  - away team
  - home team
  - away score
  - home score
  - stadium
  - created timestamp

종료 요약 메시지 규칙:
- 톤은 짧은 중립형으로 합니다.
- 첫 줄은 구독 팀 기준 경기 종료 요약임을 표시합니다.
- 최종 스코어는 원정팀과 홈팀 순서를 유지합니다.
- 승패 문장은 구독 팀 기준으로 표현합니다.
- 역전 이벤트가 없으면 역전 문장은 생략합니다.
- 역전 이벤트가 있으면 전체 역전 횟수와 마지막 역전 장면만 표시합니다.
- 마지막 줄에는 경기 시간, 구장, 최종 상태를 표시합니다.
- 이벤트 히스토리가 없거나 조회에 실패하면 역전 문장은 생략합니다.
- 봇 재시작, DB 장애, KBO 장애로 누락된 과거 이벤트는 추정하지 않습니다.

장애 가능성과 극복:
- KBO live score 조회 실패: 기존 DB의 마지막 schedule/score 데이터를 사용하고, 없으면 이번 알림 생성을 건너뜁니다.
- DB 이벤트 저장 실패: 오류를 로그로 남기고 ScoreSnapshots 갱신과 DM 발송은 가능한 범위에서 계속합니다.
- DB 이벤트 조회 실패: 역전 문장 없이 종료 요약 DM을 보냅니다.
- Discord DM 발송 실패: 기존 `markAlertDeliveryFailed` 경로를 사용해 실패 상태를 기록하고 다음 delivery를 계속 처리합니다.
- 봇 재시작: 저장된 `lead_change` 이벤트만 사용합니다. 재시작 전 저장되지 않은 흐름은 복원하지 않습니다.
- 중복 polling: event key와 delivery key로 이벤트 저장과 DM 발송을 중복 방지합니다.

리소스 예산:
- 새 타이머나 상시 background worker를 추가하지 않습니다.
- alert worker 1회 실행당 경기별 이벤트 조회는 종료 알림 대상 경기로 제한합니다.
- 이벤트 저장은 새로 감지된 `lead_change`만 수행합니다.
- 종료 요약 생성은 문자열 조합만 사용하고 외부 API나 LLM을 호출하지 않습니다.
- DB 테이블에는 필요한 index만 추가하고 대량 scan을 피합니다.
- event history 정리 정책은 Plan에서 정하되, 장기 누적으로 DB가 커지지 않게 날짜 기준 삭제 또는 보관 기간을 둡니다.

CI/CD 기준:
- `package-lock.json`을 생성해 저장소에 포함합니다.
- lockfile 도입 후 CI는 `npm ci`, `npm run check`, `npm test`, `docker build .`를 통과해야 합니다.
- schema 변경이 있으므로 database schema 테스트를 반드시 갱신합니다.
- CD는 이번 경기 종료 요약 기능 구현 범위에는 포함하지 않습니다.
- 향후 CD를 추가할 때 운영 서버에서는 build/test를 수행하지 않고, git update, conditional npm install, systemd restart만 수행합니다.
- 운영 서버 재시작 시 기존 MariaDB volume은 유지되어야 하며, `ensureSchema`는 기존 데이터 손실 없이 새 테이블을 생성해야 합니다.
- Docker 없이 systemd로 배포할 경우 운영 서버에서는 이전 revision과 새 revision의 `package.json`, `package-lock.json` 변경 여부를 비교합니다.
- 의존성 파일이 바뀐 경우에만 `npm install --omit=dev`를 실행하고, 바뀌지 않은 경우에는 install 없이 `systemctl restart kbo-discord-bot`만 실행합니다.
- restart-only CD에서 서버가 수행할 수 있는 명령은 `git fetch`, `git reset --hard`, 조건부 `npm install --omit=dev`, `systemctl restart kbo-discord-bot`로 제한합니다.

메시지 예시:

```text
LG 경기 종료 요약

KIA 3 vs 5 LG
LG가 2점 차로 승리했습니다.
역전은 2번 있었습니다. 마지막 역전은 7회말 LG가 5-3으로 앞선 장면입니다.

14:00 | 잠실 | 경기종료
```

역전이 없는 경기 예시:

```text
LG 경기 종료 요약

KIA 3 vs 5 LG
LG가 2점 차로 승리했습니다.

14:00 | 잠실 | 경기종료
```

취소 경기 예시:

```text
LG 경기 취소 안내

KIA vs LG 경기는 우천취소 상태입니다.

14:00 | 잠실 | 우천취소
```

완료 기준:
- 기존 `GAME_RESULT` 개인 DM이 종료 요약 메시지로 바뀝니다.
- 리드 팀 변경이 발생한 경기는 `lead_change` 이벤트가 저장됩니다.
- 종료 요약은 저장된 `lead_change` 이벤트 수와 마지막 이벤트를 사용합니다.
- 역전이 없는 경기는 역전 문장을 생략합니다.
- 취소 경기는 승패/역전 문장을 만들지 않습니다.
- 기존 경기 시작, 득점, 역전, 취소 알림 동작이 깨지지 않습니다.
- 기존 알림 중복 방지 정책이 유지됩니다.
- 이벤트 저장/조회 실패가 DM 발송 전체 실패로 번지지 않습니다.
- 새 기능은 기존 alert worker 외 별도 background loop를 만들지 않습니다.
- CI에서 syntax check, test, Docker build가 통과합니다.
- `package-lock.json`이 포함되고, CI가 `npm ci` 기준으로 동작합니다.

테스트 시나리오:
- 구독 팀이 승리한 종료 경기 DM에 최종 스코어와 승리 문장이 포함됩니다.
- 구독 팀이 패배한 종료 경기 DM에 최종 스코어와 패배 문장이 포함됩니다.
- 무승부 종료 경기 DM에 무승부 문장이 포함됩니다.
- 역전이 0회인 종료 경기 DM에는 역전 문장이 없습니다.
- 역전이 1회인 종료 경기 DM에는 `역전은 1번`과 마지막 역전 장면이 포함됩니다.
- 역전이 여러 번인 종료 경기 DM에는 전체 횟수와 마지막 역전 장면만 포함됩니다.
- 취소 경기 DM에는 취소 안내만 포함되고 승패/역전 문장이 없습니다.
- 같은 `lead_change` 이벤트가 반복 감지되어도 중복 저장되지 않습니다.
- 같은 경기 종료 알림이 반복 감지되어도 기존 delivery key 정책으로 중복 DM이 발송되지 않습니다.
- 이벤트 히스토리 조회 실패 시 역전 문장 없이 종료 요약이 생성됩니다.
- 이벤트 저장 실패가 발생해도 alert worker가 다음 delivery 처리를 계속합니다.
- 봇 재시작처럼 이벤트 히스토리가 비어 있는 경우 최종 스코어와 승패만 전송합니다.
- 기존 alert worker 테스트와 score event 테스트가 모두 통과합니다.

Plan 작성 시 확인할 구현 영향:
- `ScoreSnapshots`와 별도로 `lead_change` 이벤트 히스토리 테이블을 추가합니다.
- 기존 `buildScoreEvents`의 lead change 판단을 재사용하거나 확장합니다.
- alert worker는 이벤트 저장 후 종료 알림 메시지 생성에 경기별 이벤트 히스토리를 주입해야 합니다.
- DB schema 테스트, score event 테스트, alert message 테스트를 추가하거나 갱신해야 합니다.

### Phase 4: 선수/팀 정보 확장

상태: `Backlog`

목표: 조회 명령을 경기 당일 정보에서 시즌 맥락 정보로 확장합니다.

작업 후보:
- 팀 최근 경기 흐름
- 선수 시즌 스탯 확장
- 팀 상대 전적
- 부상, 엔트리, 말소 정보 조사

완료 기준:
- 출처와 갱신 주기가 불명확한 데이터는 추정처럼 보이지 않게 표시합니다.
- autocomplete와 검색 결과가 동명이인, 팀 이동, 결측 데이터를 처리합니다.

### Phase 5: 커뮤니티 기능

상태: `Backlog`

목표: Discord 서버 구성원이 경기 전후로 함께 참여할 수 있는 기능을 제공합니다.

작업 후보:
- 경기 승패 예측 투표
- 서버별 예측 랭킹
- 오늘의 직관 체크인
- 역할 자동 부여

완료 기준:
- 서버별 설정과 권한 정책이 먼저 정리되어 있어야 합니다.
- 과도한 메시지 발송을 피하는 rate/notification 정책이 있어야 합니다.

## 다음 작업 후보

1. `Phase 1` 문서 정리 완료
   - 상태: `Ready`
   - 추천 커밋 단위: 문서 기준 정리 1개 커밋
2. 경기 종료 후 개인 DM 자동 요약 Plan 작성
   - 상태: `Spec`
   - 먼저 결정할 것: 구체 DB schema, 이벤트 저장 함수 경계, alert worker 데이터 흐름
3. 운영 배포 준비 Plan 작성
   - 상태: `Spec`
   - 확정된 것: systemd 서비스 템플릿, MariaDB 소형 서버 설정, restart-only 수동 배포 스크립트, 운영 가이드
   - 남은 것: `package-lock.json` 생성, CI `npm ci` 전환, GitHub Actions restart-only CD workflow
4. 서버별 알림 채널 설정 Spec 작성
   - 상태: `Backlog`
   - 먼저 결정할 것: 서버 설정 테이블, 관리자 권한 기준, 기본값

## 문서 기반 개발 절차

1. `docs/ROADMAP.md`에서 작업 후보와 상태를 확인합니다.
2. 작업을 시작하기 전에 Spec을 작성합니다.
   - 목표
   - 범위
   - 제외 범위
   - 사용자 영향
   - 완료 기준
3. 구현 전에 Plan을 작성합니다.
   - 변경할 시스템
   - 데이터 흐름
   - 실패 모드
   - 테스트 방법
   - 커밋 단위
4. Spec과 Plan이 모두 확정된 뒤 구현합니다.
5. 각 단계가 끝날 때만 커밋합니다.
6. 머지와 배포는 사용자 요청이 있을 때만 진행합니다.

## 참고 문서

- `PLAN_FIRST_WORKFLOW.md`: 실제 작업 운영 규칙
- `README.md`: 실행과 운영 안내
- `docs/superpowers/specs/2026-05-04-kbo-discord-bot-feature-roadmap.md`: 이전 로드맵 참고 문서
- `docs/superpowers/plans/2026-05-05-discord-js-migration.md`: 완료된 JS 전환 계획 참고 문서
