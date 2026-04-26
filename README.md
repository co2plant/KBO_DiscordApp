# KBO_DiscordApp

KBO 경기 정보 Discord 봇입니다. 현재 런타임은 `discord.js` 기반 JavaScript입니다.

## 문서
- [플랜 우선 작업 흐름](PLAN_FIRST_WORKFLOW.md)

## JavaScript 개발 명령

### 의존성 설치
```bash
npm install
```

### 기본 검증
```bash
npm run check
```

### Slash command 등록
```bash
npm run deploy:commands
```

`deploy:commands`에는 유효한 `DISCORD_TOKEN`, `DISCORD_CLIENT_ID`, `DISCORD_GUILD_ID`가 필요합니다.

## 실제 실행 조건
- 유효한 Discord bot token/client/guild 설정
- MariaDB 접속 정보와 접근 가능한 DB
- Chromium/ChromeDriver 및 Selenium 실행 환경
- Discord API, KBO 사이트에 접근 가능한 네트워크

### 로컬 실행
```bash
node index.js
```

## Docker로 실행

### 1) 환경변수 파일 준비
```bash
cp .env.example .env
```

`.env`에 Discord/DB 값을 채우면 됩니다. 주요 키는 `DISCORD_TOKEN`, `DISCORD_CLIENT_ID`, `DISCORD_GUILD_ID`, `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_ROOT_PASSWORD`입니다.

### 2) 컨테이너 실행
```bash
docker compose up -d --build
```

`docker-compose.yml`에 MariaDB 서비스가 포함되어 있어 기본값 기준으로 DB도 함께 올라옵니다.

### 상태 확인
```bash
docker compose ps
docker compose logs -f bot
```

## 테스트

JavaScript 테스트는 `test/*.js`에 있으며 `npm run check`로 문법 검사와 함께 실행합니다.
