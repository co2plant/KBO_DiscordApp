# 엄격 리뷰 보고서 (2026-04)

검토 대상: 지금까지 적용된 부활/도커/안정화 변경사항 전체.

## 최종 판정
- **운영 투입 승인: 보류 (NOT APPROVED)**
- 사유: 런타임/운영 안정성 관점의 **중요 이슈(High)**가 남아 있음.

## 심각도별 이슈

### High (운영 전 반드시 수정)

1. **스케줄 루프 파라미터가 의도와 다를 가능성**
   - `@tasks.loop(hour=6)` 사용 중. `discord.ext.tasks.loop`에서 일반적으로 `hours` 또는 `time=` 패턴을 사용하며, 현재 값은 오동작 가능성이 큼.
   - 근거: `kbo.py`의 스케줄러 선언부.

2. **Selenium 드라이버 자원 해제 누락**
   - `kbo_crawler.py`의 `insert_standings()`, `update_standings()`, `update_schedule_once()`, `update_score()`에서 `driver.quit()`이 보장되지 않음.
   - 장시간 운영 시 프로세스/메모리 누수 위험.

3. **광범위한 bare except 남용**
   - DB/크롤링 코드 다수에서 `except:` 사용.
   - 실제 장애 원인(네트워크, SQL, 파싱, 인증 등) 구분 불가.

4. **헬스체크가 실제 봇 상태를 검증하지 못함**
   - compose healthcheck는 `/app/config.json` 파싱만 확인.
   - Discord 로그인 실패, DB 접속 실패, 크롤링 실패를 감지하지 못함.

### Medium (빠른 시일 내 개선 권장)

5. **의존성 버전 미고정**
   - `Dockerfile`에서 패키지를 직접 설치(`discord.py`, `selenium` 등)하며 버전 고정이 없음.
   - 재현성/롤백 안정성 저하.

6. **DB 접근 계층의 연결/트랜잭션 반복 구조**
   - 함수마다 connect/commit/close를 반복하며 예외 시 롤백/에러 전파 정책이 불명확.
   - 장기적으로 upsert 및 공통 DB 헬퍼가 필요.

7. **Slash 명령 응답 지연 대비 미흡**
   - 장시간 작업 전 `defer()`/followup 사용이 없음.
   - Discord interaction timeout 가능.

### Low (정리 권장)

8. **사용하지 않는 import와 변수 재사용 스타일 문제**
   - `kbo.py`에서 미사용 import 다수.
   - `str` 내장명 재사용 등 가독성/유지보수성 저하.

## 확인된 긍정 사항

- `database.update_standings` tuple 오타 수정 반영됨.
- `kbo_crawler.py` import-time 실행 가드 반영됨.
- `on_ready`에서 스케줄 시작 및 `before_loop` 준비 대기 로직 반영됨.
- Docker 진입점 기반 환경변수 -> `config.json` 생성 흐름은 작동 가능한 구조.

## 권고 수정 순서

1. 스케줄러 선언을 명확한 `time=` 또는 `hours=` 방식으로 수정
2. 모든 Selenium 함수에 `try/finally: driver.quit()` 보장
3. bare except 제거 + 로깅/예외 분기 도입
4. 봇 healthcheck를 실제 기능 검증 방식으로 개선 (`/health` 명령 포함)
5. `requirements.txt` 또는 `pyproject.toml`로 버전 고정

