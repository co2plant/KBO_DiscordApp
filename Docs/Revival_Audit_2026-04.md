# Revival Plan 이행 점검 (2026-04)

기준 문서: `Docs/Revival_Plan_2026.md`

## 요약
- **Phase 1 (실행 복구)**: 대부분 완료
- **Phase 2 (크롤링 안정화)**: 미완료
- **Phase 3 (운영 품질 개선)**: 미완료

## 항목별 점검

### 1) Phase 1

| 항목 | 상태 | 근거 |
|---|---|---|
| `requirements.txt` 생성/버전 고정 | ❌ 미완료 | 현재 Dockerfile에서 직접 pip 설치 중이며 requirements 파일 없음 |
| `config.json` 샘플/환경변수 주입 | ✅ 부분완료 | `docker/entrypoint.sh`가 env 기반으로 `/app/config.json` 자동 생성 |
| DB 문법 오류 수정 | ✅ 완료 | `database.update_standings`의 tuple 오타 수정됨 |
| import-time 실행 제거 | ✅ 완료 | `kbo_crawler.py`의 실행부가 `if __name__ == '__main__':`로 가드됨 |
| 스케줄러 시작 코드 추가 | ✅ 완료 | `kbo.py`의 `on_ready`에서 `update_tables.start()` 호출 |

### 2) Phase 2

| 항목 | 상태 | 근거 |
|---|---|---|
| Selenium 의존도 축소 | ❌ 미완료 | `kbo_crawler.py`, `main_sub.py`, `main_screenshot.py`에서 Selenium 사용 지속 |
| 파싱 fallback/재시도/로깅 | ❌ 미완료 | 예외 처리/재시도/구조 변경 대응 로직 부족 |
| DB upsert 구조 전환 | ❌ 미완료 | insert/update 분리 방식 유지, `ON DUPLICATE KEY UPDATE` 미도입 |

### 3) Phase 3

| 항목 | 상태 | 근거 |
|---|---|---|
| slash command 에러 핸들러 | ❌ 미완료 | `kbo.py`에 공통 에러 핸들러 없음 |
| defer/followup 적용 | ❌ 미완료 | 상호작용 지연 대응 코드 없음 |
| `/health` 명령 추가 | ❌ 미완료 | 헬스체크 slash command 없음 |

## 결론
현재 리팩토링은 **기동 안정성 확보(Phase 1 핵심)**에는 유의미한 성과가 있습니다.
다만 운영 안정성과 장애 대응력을 위한 **Phase 2~3은 아직 착수 전**입니다.

## 다음 우선순위 제안
1. `requirements.txt`(또는 `pyproject.toml`)로 의존성 고정
2. 크롤링 모듈에 재시도/타임아웃/파싱 실패 fallback 추가
3. DB 쓰기를 upsert 방식으로 통합
4. `/health` 명령과 공통 Interaction 에러 핸들러 추가
