# KBO_DiscordApp

## 문서
- [플랜 우선 작업 흐름](PLAN_FIRST_WORKFLOW.md)
- [테스트 실행 안내](tests/README.md)

## 파이썬 자동 테스트 도구
- 기본 검증 기준: `unittest` (파이썬 표준 라이브러리)
- 선택 실행: `pytest`가 설치된 경우 `unittest` 호환 테스트를 함께 실행 가능

### 테스트 실행
```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

### 단계별 검증 예시
```bash
python3 -m unittest tests.test_crawler_cleanup tests.test_settings_validation tests.test_runtime_guard -v
python3 -m py_compile settings.py kbo.py kbo_crawler.py
```

## 여기(개발 컨테이너)에서 디스코드 실제 실행 가능한가?
- **가능은 하지만 조건이 필요합니다.**
  1. `config.json`에 유효한 `DISCORD.TOKEN`, `CHANNEL_ID`, `GUILD_ID` 설정
  2. DB 접속 정보(`MARIA`) 설정 및 대상 DB 접근 가능
  3. Chrome/ChromeDriver 및 Selenium 실행 환경 준비
  4. 네트워크에서 Discord API, KBO 사이트 접근 가능

- 위 조건이 없으면 이 컨테이너에서는 **문법 체크/단위 테스트까지만** 검증 가능합니다.

### 실제 실행 명령
```bash
python kbo.py
```

## Docker로 고정 실행 (매번 설정 다시 안 쓰는 방법)
네, 가능합니다. 이 저장소에는 Docker 기반 실행 파일을 추가했습니다.

### 1) 환경변수 파일 준비
```bash
cp .env.example .env
```

`.env`에 디스코드/DB 값을 채우면 됩니다.

DB 관련 주요 키는 `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_ROOT_PASSWORD` 입니다.

### 2) 컨테이너 실행
```bash
docker compose up -d --build
```

### 동작 방식
- `/app/config.json`이 없으면 엔트리포인트가 `.env` 값을 이용해 자동 생성합니다.
- 따라서 운영 중에는 `.env`만 관리하면 되고, 매번 `config.json`을 수동 작성할 필요가 없습니다.
- `docker-compose.yml`에 MariaDB 서비스가 포함되어 있어, 기본값 기준으로 DB도 함께 올라옵니다.

### 상태 확인
```bash
docker compose ps
docker compose logs -f bot
```
