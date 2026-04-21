# KBO_DiscordApp

## 문서
- [2026 부활 가이드](Docs/Revival_Plan_2026.md)
- [2026 부활 점검 리포트](Docs/Revival_Audit_2026-04.md)
- [다음 작업 보고서](Docs/Next_Steps_2026-04.md)
- [엄격 리뷰 보고서](Docs/Strict_Review_2026-04.md)
- [초엄격 리뷰 보고서](Docs/Ultra_Strict_Review_2026-04.md)
- [운영 승인 체크리스트](Docs/Production_Approval_Checklist_2026-04.md)

## 파이썬 자동 테스트 도구
- 기본 내장: `unittest` (파이썬 표준 라이브러리)
- 실무에서 많이 사용: `pytest` (간결한 문법/강력한 fixture)

### 테스트 실행
```bash
python -m unittest discover -s tests -p 'test_*.py'
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
