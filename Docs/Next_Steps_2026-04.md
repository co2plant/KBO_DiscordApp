# 다음 작업 보고서 (2026-04)

기준:
- `Docs/Revival_Plan_2026.md`
- `Docs/Revival_Audit_2026-04.md`

## 현재 상태 요약
- Phase 1 핵심 안정화(스케줄러 시작, crawler import 가드, DB tuple 오류)는 반영됨.
- Docker 기반 실행 경로와 기본 테스트도 준비됨.
- 아직 실서비스 안정성을 위해 필요한 Phase 2~3 항목이 남아 있음.

## 우선순위별 다음 작업

### P1 (가장 먼저)
1. **의존성 고정 파일 추가**
   - `requirements.txt` 또는 `pyproject.toml` 작성
   - Dockerfile도 해당 파일 기반 설치로 전환
   - 목표: 환경마다 버전 차이로 인한 실행 실패 방지

2. **DB 업서트(upsert) 구조 도입**
   - `insert_game_and_score`/`update_standings` 흐름을 정리
   - `ON DUPLICATE KEY UPDATE` 패턴으로 중복/갱신 처리 일원화
   - 목표: 크롤링 재실행 시 데이터 정합성 보장

3. **크롤링 실패 안전장치 추가**
   - Selenium 파싱 실패 시 예외 메시지/재시도
   - 타임아웃, 요소 미존재 fallback
   - 목표: 사이트 구조 변경 시 봇 전체 장애 방지

### P2 (그 다음)
4. **Discord Interaction 운영 품질 보강**
   - 공통 에러 핸들러 추가
   - 느린 크롤링 경로에 `defer`/followup 적용
   - 목표: 사용자 체감 오류 감소

5. **헬스체크 slash command 추가 (`/health`)**
   - DB 연결 확인
   - 최신 크롤링 시각 확인
   - 당일 경기 데이터 건수 확인
   - 목표: 운영자가 장애 원인을 즉시 판단

### P3 (운영 마무리)
6. **관측성(로그) 정리**
   - 크롤링 성공/실패/소요시간/건수 구조화 로그
   - 오류 레벨 분리

7. **테스트 확장**
   - AST 테스트 외에 DB 함수 mock 기반 단위 테스트
   - crawler 파싱 함수 분리 후 파서 테스트 추가

## 제안 일정
- Day 1: 의존성 고정 + Dockerfile 반영
- Day 2: DB upsert 전환
- Day 3: 크롤링 재시도/fallback + 에러 핸들러
- Day 4: `/health` 명령 + 로그 정리
- Day 5: 테스트 확장 및 배포 점검

## 즉시 착수 추천 1건
가장 먼저는 **의존성 고정(requirements/pyproject) + Dockerfile 연동**입니다.
이 작업을 먼저 해야 이후 수정사항이 팀원/서버 환경에서 동일하게 재현됩니다.
