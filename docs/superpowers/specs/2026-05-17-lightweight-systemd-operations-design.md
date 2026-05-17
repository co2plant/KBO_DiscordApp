# Lightweight systemd Operations Design

작성일: 2026-05-17

## 목적

KBO Discord Bot의 공식 운영 방식을 Docker 기반에서 Ubuntu 서버 직접 실행 방식으로 전환한다. 운영 서버는 1 vCPU, 1GB RAM 기준이므로, 서버에서 build/test/Jenkins/Docker build를 실행하지 않고 systemd로 Node 프로세스만 안정적으로 관리한다.

## 확정 결정

- 공식 운영 방식은 Ubuntu + systemd 직접 실행이다.
- Docker는 공식 지원에서 제거한다.
- CI는 GitHub Actions에서 Node 검증만 수행한다.
- CD workflow는 이번 작업에 포함하지 않는다.
- 향후 CD는 restart-only 방식만 허용한다.
- 운영 서버에서는 test/build/Docker build/Jenkins를 실행하지 않는다.
- Node.js는 NodeSource apt repo로 설치한 Node.js 22를 사용한다.
- systemd는 `/usr/bin/node src/index.js`를 실행한다.
- 앱 경로는 `/home/ubuntu/workspace/KBO_DiscordApp`이다.
- 서버 사용자는 `ubuntu`이다.
- MariaDB는 같은 서버에 직접 설치한다.
- Chromium은 apt로 설치하고 headless 실행에 사용한다.
- 수동 DB 백업 명령은 문서화하지만 자동 백업은 이번 범위에서 제외한다.

## 범위

포함:
- `Dockerfile` 제거
- `docker-compose.yml` 제거
- README의 Docker 실행 안내 제거
- README를 systemd 운영 문서로 연결
- `docs/OPERATIONS.md`를 공식 운영 가이드로 정리
- systemd 서비스 템플릿 제공
- MariaDB 소형 서버 설정 제공
- restart-only 수동 배포 스크립트 제공
- `package-lock.json` 생성
- GitHub Actions CI를 `npm ci`, `npm run check`, `npm test`로 정리

제외:
- GitHub Actions CD workflow 추가
- 서버에 실제 패키지 설치
- 서버 systemd 서비스 실제 등록
- MariaDB 실제 생성 또는 데이터 마이그레이션
- 경기 종료 자동 요약 기능 구현
- 자동 백업 cron 또는 systemd timer 추가

## 운영 아키텍처

서버는 하나의 Ubuntu 인스턴스에서 Node 앱, MariaDB, headless Chromium을 운영한다. Node 앱은 systemd가 관리하고, MariaDB는 OS 서비스로 실행한다. Chromium은 상시 실행하지 않고 KBO 순위/일정 크롤링이 필요할 때만 `puppeteer-core`가 headless 프로세스로 실행한다.

기준 값:
- Service name: `kbo-discord-bot`
- User/Group: `ubuntu`
- WorkingDirectory: `/home/ubuntu/workspace/KBO_DiscordApp`
- EnvironmentFile: `/home/ubuntu/workspace/KBO_DiscordApp/.env`
- ExecStart: `/usr/bin/node src/index.js`
- Restart policy: `Restart=always`, `RestartSec=10`
- Chromium path: `/usr/bin/chromium`

## 의존성 관리와 CI

`package-lock.json`을 저장소에 포함한다. lockfile 도입 후 GitHub Actions는 `npm install`이 아니라 `npm ci`를 사용한다.

CI 범위:
- checkout
- setup-node 22
- `npm ci`
- `npm run check`
- `npm test`

CI에서 제거할 것:
- Docker build job
- 배포 job
- audit 또는 shellcheck 같은 추가 검사는 이번 범위에서 제외한다.

운영 서버 의존성 설치 기준:
- 매 배포마다 `npm install`을 실행하지 않는다.
- 이전 revision과 새 revision 사이에서 `package.json` 또는 `package-lock.json`이 바뀐 경우에만 `npm install --omit=dev`를 실행한다.
- 의존성 파일 변경이 없으면 systemd restart만 수행한다.

## 수동 restart-only 배포

이번 작업은 CD workflow를 추가하지 않는다. 대신 같은 명령 흐름을 수동으로 실행할 수 있는 스크립트 템플릿을 제공한다.

서버에서 허용되는 배포 작업:
- `git fetch`
- `git reset --hard origin/main`
- 조건부 `npm install --omit=dev`
- `sudo systemctl restart kbo-discord-bot`

서버에서 금지되는 배포 작업:
- `npm test`
- `docker build`
- 일반 build 작업
- Jenkins 실행

## MariaDB 운영

MariaDB는 같은 서버에 직접 설치한다. 1GB RAM 서버이므로 기본값보다 작은 설정을 제공한다.

기준 설정:
- `innodb_buffer_pool_size=128M`
- `max_connections=20`
- `performance_schema=OFF`
- `table_open_cache=200`
- `tmp_table_size=16M`
- `max_heap_table_size=16M`

수동 백업은 `mysqldump` 기준으로 문서화한다. 자동 백업 스케줄러는 이번 작업에 포함하지 않는다.

## 환경 변수

서버의 `.env`는 저장소에 커밋하지 않는다. `.env.example`에는 운영에 필요한 키 이름만 제공한다.

필수 운영 값:
- `DISCORD_TOKEN`
- `DISCORD_CHANNEL_ID`
- `DISCORD_GUILD_ID`
- `DB_HOST=127.0.0.1`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium`

## 장애 대응

systemd:
- 프로세스가 죽으면 자동 재시작한다.
- 로그는 `journalctl -u kbo-discord-bot -f`로 확인한다.

MariaDB:
- 소형 설정으로 메모리 사용량을 제한한다.
- 자동 백업은 제외하지만 수동 백업 명령을 문서화한다.

Chromium:
- GUI 없이 headless로만 실행한다.
- 필요할 때만 실행되고 크롤링 후 종료되어야 한다.

배포:
- 서버에서 테스트나 build를 실행하지 않는다.
- 의존성 변경이 없으면 restart만 수행한다.

## 문서 변경

README:
- Docker 실행 섹션을 제거한다.
- 운영 문서 링크를 유지한다.
- 로컬 테스트 명령은 유지한다.

`docs/OPERATIONS.md`:
- Ubuntu 서버 준비
- Node.js 22 설치
- Chromium 설치
- MariaDB 설치와 소형 설정
- `.env` 작성
- systemd 서비스 등록
- 수동 restart-only 배포
- 수동 DB 백업 명령

`docs/ROADMAP.md`:
- Docker 없는 systemd 운영 기준을 공식 방향으로 반영한다.
- 운영 배포 준비 작업의 남은 항목을 lockfile, CI 전환, 선택적 CD workflow로 정리한다.

## 완료 기준

- `Dockerfile`과 `docker-compose.yml`이 제거된다.
- README에서 Docker 실행 안내가 사라진다.
- CI에서 Docker build job이 제거된다.
- CI가 `npm ci`, `npm run check`, `npm test` 기준으로 동작한다.
- `package-lock.json`이 저장소에 포함된다.
- systemd 서비스 템플릿이 있다.
- MariaDB 소형 서버 설정 템플릿이 있다.
- restart-only 수동 배포 스크립트가 있다.
- `docs/OPERATIONS.md`가 Ubuntu + systemd 운영 기준을 설명한다.
- `git diff --check`가 통과한다.
- npm이 있는 환경에서 `npm ci`와 `npm test`가 통과한다.

## 후속 작업

1. 서버 초기 세팅
   - Node.js 22 설치
   - MariaDB 설치와 계정 생성
   - Chromium 설치
   - `.env` 작성
   - systemd 서비스 등록
2. 경기 종료 자동 요약 기능
   - `lead_change` 이벤트 저장
   - 종료 DM 요약 메시지
   - 장애 fallback
3. restart-only CD
   - GitHub Actions SSH 배포
   - 조건부 npm install
   - systemd restart
