# Operations Guide

이 문서는 Docker 없이 Ubuntu 서버에서 KBO Discord Bot을 운영하기 위한 기준입니다.

## 기준

- 서버 사용자: `ubuntu`
- 앱 경로: `/home/ubuntu/workspace/KBO_DiscordApp`
- 프로세스 관리자: systemd
- Node.js: NodeSource apt repo로 설치한 Node.js 22, `/usr/bin/node`
- DB: 같은 서버에 직접 설치한 MariaDB
- 브라우저: apt로 설치한 Chromium
- 서버 리소스 기준: 1 vCPU, 1GB RAM

## 서버 패키지

Node.js는 nvm 대신 NodeSource apt repo로 설치합니다. systemd에서 nvm 경로를 쓰면 PATH와 login shell 의존성이 생기므로 피합니다.

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs
```

Chromium과 한글 폰트를 설치합니다.

```bash
sudo apt-get update
sudo apt-get install -y chromium fonts-nanum ca-certificates
```

Chromium 경로를 확인합니다.

```bash
which chromium
```

기본값은 `/usr/bin/chromium`입니다. 다른 경로가 나오면 `.env`의 `PUPPETEER_EXECUTABLE_PATH`를 실제 경로로 맞춥니다.

## MariaDB

같은 서버에 MariaDB를 직접 설치합니다.

```bash
sudo apt-get install -y mariadb-server
sudo systemctl enable --now mariadb
```

1GB RAM 서버에서는 소형 설정을 적용합니다.

```bash
sudo cp ops/mariadb/60-kbo-small.cnf /etc/mysql/mariadb.conf.d/60-kbo-small.cnf
sudo systemctl restart mariadb
```

데이터베이스와 계정은 `.env`의 값에 맞춰 생성합니다.

```sql
CREATE DATABASE kbo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'app_user'@'localhost' IDENTIFIED BY 'app_password';
GRANT ALL PRIVILEGES ON kbo.* TO 'app_user'@'localhost';
FLUSH PRIVILEGES;
```

실제 비밀번호는 공개 문서나 GitHub에 커밋하지 않습니다.

## 앱 배치

앱은 아래 경로에 둡니다.

```bash
mkdir -p /home/ubuntu/workspace
cd /home/ubuntu/workspace
git clone https://github.com/co2plant/KBO_DiscordApp.git
cd KBO_DiscordApp
```

의존성은 운영 패키지만 설치합니다.

```bash
npm install --omit=dev
```

`package-lock.json`이 저장소에 추가된 뒤에는 CI는 `npm ci`를 사용하고, 운영 서버는 의존성 파일이 바뀐 배포에서만 `npm install --omit=dev`를 실행합니다.

## 환경 변수

`.env.example`을 복사해서 서버의 `.env`를 만듭니다.

```bash
cp .env.example .env
chmod 600 .env
```

운영 서버에서는 보통 DB host를 localhost로 둡니다.

```env
DB_HOST=127.0.0.1
PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
```

Discord token, DB password, 서버 IP, SSH private key는 GitHub에 커밋하지 않습니다.

## systemd

서비스 파일을 설치합니다.

```bash
sudo cp ops/systemd/kbo-discord-bot.service /etc/systemd/system/kbo-discord-bot.service
sudo systemctl daemon-reload
sudo systemctl enable --now kbo-discord-bot
```

상태와 로그를 확인합니다.

```bash
sudo systemctl status kbo-discord-bot
journalctl -u kbo-discord-bot -f
```

재시작은 아래 명령으로 합니다.

```bash
sudo systemctl restart kbo-discord-bot
```

## 수동 배포

서버 부하를 줄이기 위해 테스트와 build는 서버에서 실행하지 않습니다.

```bash
DEPLOY_PATH=/home/ubuntu/workspace/KBO_DiscordApp ops/deploy-restart-only.sh
```

스크립트는 다음 작업만 수행합니다.

- `git fetch`
- `git reset --hard origin/main`
- `package.json` 또는 `package-lock.json` 변경 시에만 `npm install --omit=dev`
- `systemctl restart kbo-discord-bot`

## CI/CD 정책

- CI는 GitHub Actions에서 실행합니다.
- 운영 서버에서는 `npm test`, `docker build`, Jenkins를 실행하지 않습니다.
- CD를 추가할 경우 restart-only 방식만 사용합니다.
- restart-only CD에서 서버가 수행할 명령은 git update, 조건부 npm install, systemd restart로 제한합니다.

## 현재 남은 운영 준비 작업

- npm이 있는 환경에서 `package-lock.json` 생성
- lockfile 생성 후 `.github/workflows/ci.yml`의 install step을 `npm ci`로 변경
- 서버에 Node.js 22, MariaDB, Chromium 설치
- 서버 `.env` 작성
- systemd 서비스 설치
