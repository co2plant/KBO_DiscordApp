# KBO_DiscordApp

KBO 정보를 제공하는 Discord 봇입니다. 현재 런타임은 **Node.js + discord.js** 입니다.

## 주요 명령어

- `/순위`: KBO 팀 순위
- `/성적`: 선택한 팀의 상세 성적
- `/일정`: 오늘/내일/모레 경기 일정
- `/팀`: 선택한 팀의 오늘 경기와 성적 요약
- `/경기요약`: 선택한 팀의 오늘 경기 흐름 요약
- `/선수`: 선수 이름으로 KBO 기본 정보 조회
- `/내팀설정`, `/내팀`, `/내팀해제`: 개인 기본 팀 설정
- `/알림설정`, `/알림해제`, `/내알림`: 개인 DM 알림 설정
- `/도움말`: 사용법과 주요 명령어 확인

## 환경변수

`.env.example`을 복사해 `.env`를 만들고 값을 채우세요.

```powershell
Copy-Item .env.example .env
```

필수 값:

```env
DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN
DISCORD_CHANNEL_ID=123456789012345678
DISCORD_GUILD_ID=123456789012345678

DB_HOST=localhost
DB_USER=app_user
DB_PASSWORD=app_password
DB_NAME=kbo
PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
```

## 운영 실행

공식 운영 방식은 Docker가 아니라 Ubuntu + systemd 직접 실행입니다. 서버 준비, MariaDB, Chromium, systemd 등록 절차는 `docs/OPERATIONS.md`를 따릅니다.

로컬에서 실제 봇을 실행하려면 Node.js 22와 npm으로 의존성을 설치한 뒤 실행합니다.

```powershell
npm install
npm start
```

스코어 갱신이 실행되면 로그에 다음 형태가 출력됩니다.

```text
[crawl:live-score] date=0505 scoreboard_games=5
[crawl:live-score] 14:00 두산 0-0 LG 경기전
```

## 로컬 테스트

외부 패키지 설치 없이 파서/formatter 테스트는 번들 Node로 실행할 수 있습니다.

```powershell
node --test --test-isolation=none
node --check src/index.js
```

실제 봇 실행에는 `discord.js`, `mysql2`, `puppeteer-core` 설치가 필요합니다.

## 개발 문서

- 기준 로드맵: `docs/ROADMAP.md`
- 작업 절차: `PLAN_FIRST_WORKFLOW.md`
- 운영 가이드: `docs/OPERATIONS.md`
