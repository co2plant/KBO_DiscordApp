# KBO Discord Bot 재사용(부활) 가이드 (2026-04 기준)

이 문서는 현재 코드베이스를 기준으로, 봇을 다시 실사용 가능한 상태로 복구하기 위한 단계별 계획입니다.

## 1) 먼저 확인할 최신 discord.py 기준점

- **현재 최신 안정 버전(확인 시점)**: `discord.py 2.7.1` (2026-03-03 배포)
- v2.7.0~2.7.1 구간에서 주목할 포인트
  - 음성 연결 관련 DAVE 프로토콜 지원
  - Modal/컴포넌트 관련 기능 확장
  - 각종 버그 수정(뷰 캐시/웹소켓/명령 계층)
- 참고 링크
  - https://pypi.org/project/discord.py/
  - https://discordpy.readthedocs.io/en/latest/whats_new.html

> 현재 저장소는 슬래시 커맨드(`app_commands`)를 이미 사용하고 있어, 큰 방향은 맞습니다.

## 2) 현재 코드 상태에서 우선 수정해야 할 리스크

### A. 스케줄러가 실제로 시작되지 않음
- `@tasks.loop` 로 정의된 `update_tables()`가 있지만, `start()` 호출이 없어 자동 실행되지 않습니다.
- 위치: `main_sub.py`

### B. 크롤러 모듈 import 시 즉시 실행되는 구조
- `kbo_crawler.py` 하단의 `insert_schedule_month()`가 import만 해도 실행됩니다.
- 운영 봇에서는 매우 위험(예: 부팅 시 원치 않는 DB 대량 쓰기).
- 위치: `kbo_crawler.py`

### C. DB 업데이트 함수의 치명적 문법 오류
- `database.update_standings()` 내 튜플 생성에서 오타(`game_info[9]. game_info[0]`)가 있어 런타임 오류가 발생합니다.
- 위치: `database.py`

### D. Selenium 크롤링의 운영 안정성 부족
- `webdriver.Chrome(options)` 패턴 사용 시 환경에 따라 드라이버 경로/버전 문제 발생 가능.
- 페이지 구조 변경 시 XPATH 기반 파싱이 깨질 가능성 큼.
- 위치: `kbo_crawler.py`, `main_sub.py`, `main_screenshot.py`

## 3) 현실적인 부활 전략 (권장 순서)

### Phase 1. 실행 복구 (1~2일)
1. Python/패키지 버전 고정
   - Python 3.11 또는 3.12 권장
   - `requirements.txt` 신설 후 버전 고정
2. `config.json` 샘플 파일 추가
   - 토큰/DB 정보는 환경변수로 주입하도록 변경 권장
3. 크리티컬 버그 먼저 제거
   - `database.py` 문법 오류 수정
   - `kbo_crawler.py`의 import-time 실행 제거 (`if __name__ == '__main__':`로 가드)
4. 봇 시작 시 스케줄러 명시적 시작
   - `on_ready` 또는 `setup_hook`에서 `update_tables.start()`

### Phase 2. 크롤링 안정화 (2~4일)
1. Selenium 의존도 축소 검토
   - 가능하면 requests + BeautifulSoup 방식으로 전환
2. 파싱 로직에 안전장치 추가
   - 요소 없음/구조 변경 시 fallback 메시지
   - 타임아웃/재시도/로깅
3. DB upsert 구조로 전환
   - 중복 insert 에러보다 `ON DUPLICATE KEY UPDATE` 방식 권장

### Phase 3. Discord 운영 품질 개선 (1~2일)
1. slash command 에러 핸들러 추가
2. 응답 시간을 고려한 `defer`/followup 적용
3. 관리자용 헬스체크 명령 추가
   - `/health` : DB 연결, 최근 크롤링 시간, 오늘 경기 건수 점검

## 4) discord.py 최신 흐름에서 특히 신경 쓸 점

1. **Intents 재검증**
   - 지금 코드는 기본 intents만 사용하며 메시지 content intent가 필요 없는 구조(슬래시 기반)라 비교적 안전합니다.
2. **Interaction 중심 설계 유지**
   - 텍스트 접두사 명령보다 slash command 유지가 장기적으로 유리합니다.
3. **UI/컴포넌트 확장 가능성**
   - 추후 버튼(다음날/전날 일정) 또는 Modal(팀 필터 입력) 추가 시 2.7 계열 기능 활용 여지가 큼.

## 5) 추천 운영 아키텍처(간단)

- **bot 프로세스**: 디스코드 상호작용 처리
- **crawler 작업**: 별도 주기 실행(Cron/GitHub Actions/서버 스케줄러)
- **DB**: 최종 결과만 저장

이렇게 분리하면, Discord 연결 장애와 크롤링 장애를 독립적으로 다룰 수 있습니다.

## 6) 바로 실행 가능한 체크리스트

- [ ] `requirements.txt` 생성 및 설치 검증
- [ ] DB 함수 문법 오류 수정
- [ ] import-time 실행 제거
- [ ] 스케줄러 시작 코드 추가
- [ ] 크롤링 실패 시 사용자 메시지 정리
- [ ] 최소 로그(성공/실패/건수/소요시간) 도입

---

원하시면 다음 작업으로, 위 문서 기준 **Phase 1(실행 복구) 패치**를 바로 적용해 드릴 수 있습니다.
