# KBO_DiscordApp

KBO 정보를 제공하는 Discord 봇입니다. 현재 런타임은 **Node.js + discord.js** 입니다.

## 주요 명령어

- `/순위`: KBO 팀 순위
- `/성적`: 선택한 팀의 상세 성적
- `/일정`: 오늘/내일/모레 경기 일정
- `/스코어`: 오늘 경기 스코어, 경기 중에는 KBO live score 재크롤링
- `/팀`: 선택한 팀의 오늘 경기와 성적 요약

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

DB_HOST=mariadb
DB_USER=app_user
DB_PASSWORD=app_password
DB_NAME=kbo
DB_ROOT_PASSWORD=rootpass
```

## Docker 실행

```powershell
docker compose up -d --build
```

상태와 로그 확인:

```powershell
docker compose ps
docker compose logs -f bot
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

실제 봇 실행에는 `discord.js`, `mysql2`, `puppeteer-core` 설치가 필요합니다. Docker 실행을 권장합니다.
