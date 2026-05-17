# Lightweight systemd Operations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace official Docker-based operation with lightweight Ubuntu + systemd operation, lock dependency installs with `package-lock.json`, and simplify CI to Node checks only.

**Architecture:** The bot runs directly on Ubuntu under systemd using `/usr/bin/node src/index.js`. MariaDB and Chromium are installed on the host, and CI runs only `npm ci`, syntax check, and tests on GitHub Actions. Deployment automation is limited to a restart-only script; no CD workflow is added in this plan.

**Tech Stack:** Node.js 22, npm, GitHub Actions, systemd, MariaDB, Chromium, Bash.

---

## Scope Check

This plan covers one subsystem: lightweight operations and CI. It does not implement the game result summary feature, actual server provisioning, or GitHub Actions CD. Those remain separate roadmap items.

## File Structure

- `.github/workflows/ci.yml`: Node-only CI workflow.
- `package-lock.json`: npm lockfile generated from `package.json`.
- `Dockerfile`: remove because Docker is no longer official operation.
- `docker-compose.yml`: remove because Docker Compose is no longer official operation.
- `.env.example`: include Chromium executable path.
- `README.md`: remove Docker run instructions and link to operations docs.
- `docs/OPERATIONS.md`: official Ubuntu + systemd operations guide.
- `docs/ROADMAP.md`: reflect Docker removal, Node-only CI, and operation status.
- `ops/systemd/kbo-discord-bot.service`: systemd unit template.
- `ops/mariadb/60-kbo-small.cnf`: 1 vCPU / 1GB RAM MariaDB config.
- `ops/deploy-restart-only.sh`: manual restart-only deployment script.

User instruction: do not create commits automatically. Each task ends with a user commit checkpoint and a suggested commit message.

---

### Task 1: Generate npm Lockfile

**Files:**
- Create: `package-lock.json`
- Read: `package.json`

- [ ] **Step 1: Confirm npm is available**

Run:

```powershell
npm -v
node -v
```

Expected:
- `npm -v` prints a version.
- `node -v` prints Node 22 or newer.

If npm is not available in the current environment, stop this task and run it in an environment with Node.js/npm installed. Do not hand-write `package-lock.json`.

- [ ] **Step 2: Generate lockfile without installing runtime dependencies into the repo**

Run:

```powershell
npm install --package-lock-only
```

Expected:
- `package-lock.json` is created.
- `package.json` remains unchanged unless npm normalizes metadata.
- `node_modules/` is not required to be committed.

- [ ] **Step 3: Verify clean locked install**

Run:

```powershell
npm ci
```

Expected:
- Dependencies install from `package-lock.json`.
- Command exits 0.
- `node_modules/` remains untracked because `.gitignore` excludes it.

- [ ] **Step 4: Verify current Node checks**

Run:

```powershell
npm run check
npm test
```

Expected:
- `npm run check` exits 0.
- `npm test` exits 0 with all existing tests passing.

- [ ] **Step 5: User commit checkpoint**

Suggested commit message:

```text
build: add npm lockfile
```

Do not commit automatically; report the suggested message to the user.

---

### Task 2: Simplify GitHub Actions CI

**Files:**
- Modify: `.github/workflows/ci.yml`
- Delete: `Dockerfile`
- Delete: `docker-compose.yml`

- [ ] **Step 1: Replace CI workflow with Node-only checks**

Replace `.github/workflows/ci.yml` with:

```yaml
name: CI

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main
  workflow_dispatch:

permissions:
  contents: read

jobs:
  test:
    name: Check and test
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm

      - name: Install dependencies
        run: npm ci

      - name: Run syntax check
        run: npm run check

      - name: Run tests
        run: npm test
```

- [ ] **Step 2: Remove Docker artifacts**

Delete:

```text
Dockerfile
docker-compose.yml
```

Expected:
- No official Docker build or Compose run path remains in the repository.
- CI no longer references `docker build`.

- [ ] **Step 3: Search for stale Docker operation references**

Run:

```powershell
rg -n "Docker|docker compose|docker build|Compose|container" README.md docs .github ops
```

Expected:
- No README or official operations docs tell users to run Docker.
- Historical notes may exist only if explicitly marked as archived/reference.

- [ ] **Step 4: Verify CI syntax-related files**

Run:

```powershell
npm run check
npm test
git diff --check
```

Expected:
- Node syntax check passes.
- Tests pass.
- No whitespace errors.

- [ ] **Step 5: User commit checkpoint**

Suggested commit message:

```text
ci: use npm ci and remove docker build
```

Do not commit automatically; report the suggested message to the user.

---

### Task 3: Finalize Operations Templates

**Files:**
- Create or replace: `ops/systemd/kbo-discord-bot.service`
- Create or replace: `ops/mariadb/60-kbo-small.cnf`
- Create or replace: `ops/deploy-restart-only.sh`
- Modify: `.env.example`

- [ ] **Step 1: Write systemd unit template**

Set `ops/systemd/kbo-discord-bot.service` to:

```ini
[Unit]
Description=KBO Discord Bot
After=network-online.target mariadb.service
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/workspace/KBO_DiscordApp
Environment=NODE_ENV=production
EnvironmentFile=/home/ubuntu/workspace/KBO_DiscordApp/.env
ExecStart=/usr/bin/node src/index.js
Restart=always
RestartSec=10
KillSignal=SIGTERM
TimeoutStopSec=30
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 2: Write MariaDB small-server config**

Set `ops/mariadb/60-kbo-small.cnf` to:

```ini
[mysqld]
# Small-server baseline for a 1 vCPU / 1GB RAM host running MariaDB and the bot.
innodb_buffer_pool_size=128M
max_connections=20
performance_schema=OFF
table_open_cache=200
tmp_table_size=16M
max_heap_table_size=16M
```

- [ ] **Step 3: Write restart-only deployment script**

Set `ops/deploy-restart-only.sh` to:

```bash
#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${DEPLOY_PATH:-/home/ubuntu/workspace/KBO_DiscordApp}"
SERVICE_NAME="${SERVICE_NAME:-kbo-discord-bot}"
BRANCH="${DEPLOY_BRANCH:-main}"

cd "$APP_DIR"

OLD_REV="$(git rev-parse HEAD)"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"
NEW_REV="$(git rev-parse HEAD)"

if git diff --name-only "$OLD_REV" "$NEW_REV" | grep -Eq '^(package.json|package-lock.json)$'; then
  npm install --omit=dev
fi

sudo systemctl restart "$SERVICE_NAME"
```

- [ ] **Step 4: Mark deployment script executable in git**

Run:

```powershell
git update-index --chmod=+x ops/deploy-restart-only.sh
```

Expected:
- Git records executable bit for the script.

- [ ] **Step 5: Add Chromium path to env example**

Ensure `.env.example` contains:

```env
# Browser
PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
```

Keep existing Discord and MariaDB variables.

- [ ] **Step 6: Verify templates contain no secrets**

Run:

```powershell
rg -n "DISCORD_TOKEN=.+|DB_PASSWORD=.+|PRIVATE KEY|BEGIN OPENSSH|DEPLOY_HOST|DEPLOY_SSH_KEY" .env.example docs ops
```

Expected:
- No real tokens, passwords, private keys, server IPs, or hostnames are present.
- Placeholder values in `.env.example` are acceptable.

- [ ] **Step 7: User commit checkpoint**

Suggested commit message:

```text
ops: add systemd and restart-only deployment templates
```

Do not commit automatically; report the suggested message to the user.

---

### Task 4: Rewrite Official Operations Documentation

**Files:**
- Create or replace: `docs/OPERATIONS.md`
- Modify: `README.md`
- Modify: `docs/ROADMAP.md`

- [ ] **Step 1: Ensure operations guide covers server prerequisites**

`docs/OPERATIONS.md` must include these exact operational facts:

```text
서버 사용자: ubuntu
앱 경로: /home/ubuntu/workspace/KBO_DiscordApp
프로세스 관리자: systemd
Node.js: NodeSource apt repo로 설치한 Node.js 22, /usr/bin/node
DB: 같은 서버에 직접 설치한 MariaDB
브라우저: apt로 설치한 Chromium
서버 리소스 기준: 1 vCPU, 1GB RAM
```

- [ ] **Step 2: Document Node.js and Chromium installation**

`docs/OPERATIONS.md` must include:

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs
```

and:

```bash
sudo apt-get update
sudo apt-get install -y chromium fonts-nanum ca-certificates
which chromium
```

State that `.env` should use:

```env
PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
```

- [ ] **Step 3: Document MariaDB installation and small-server config**

`docs/OPERATIONS.md` must include:

```bash
sudo apt-get install -y mariadb-server
sudo systemctl enable --now mariadb
sudo cp ops/mariadb/60-kbo-small.cnf /etc/mysql/mariadb.conf.d/60-kbo-small.cnf
sudo systemctl restart mariadb
```

and the SQL template:

```sql
CREATE DATABASE kbo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'app_user'@'localhost' IDENTIFIED BY 'app_password';
GRANT ALL PRIVILEGES ON kbo.* TO 'app_user'@'localhost';
FLUSH PRIVILEGES;
```

State that actual passwords must not be committed.

- [ ] **Step 4: Document systemd install and logs**

`docs/OPERATIONS.md` must include:

```bash
sudo cp ops/systemd/kbo-discord-bot.service /etc/systemd/system/kbo-discord-bot.service
sudo systemctl daemon-reload
sudo systemctl enable --now kbo-discord-bot
sudo systemctl status kbo-discord-bot
journalctl -u kbo-discord-bot -f
sudo systemctl restart kbo-discord-bot
```

- [ ] **Step 5: Document manual restart-only deployment**

`docs/OPERATIONS.md` must include:

```bash
DEPLOY_PATH=/home/ubuntu/workspace/KBO_DiscordApp ops/deploy-restart-only.sh
```

Document that the script only performs:

```text
git fetch
git reset --hard origin/main
package.json or package-lock.json changed -> npm install --omit=dev
systemctl restart kbo-discord-bot
```

- [ ] **Step 6: Document manual MariaDB backup only**

Add a `수동 DB 백업` section to `docs/OPERATIONS.md` with:

```bash
cd /home/ubuntu/workspace/KBO_DiscordApp
set -a
. ./.env
set +a
mkdir -p /home/ubuntu/backups/kbo
cat > /tmp/kbo-mysqldump.cnf <<EOF
[client]
host=$DB_HOST
user=$DB_USER
password=$DB_PASSWORD
EOF
chmod 600 /tmp/kbo-mysqldump.cnf
mysqldump --defaults-extra-file=/tmp/kbo-mysqldump.cnf "$DB_NAME" > "/home/ubuntu/backups/kbo/kbo-$(date +%F-%H%M%S).sql"
rm -f /tmp/kbo-mysqldump.cnf
```

State that automatic backup scheduling is a later task.

- [ ] **Step 7: Update README official operation section**

Remove the Docker execution section entirely. Add:

```markdown
## 운영

공식 운영 방식은 Docker가 아니라 Ubuntu + systemd 직접 실행입니다. 서버 준비, MariaDB, Chromium, systemd 등록 절차는 `docs/OPERATIONS.md`를 따릅니다.
```

Keep the local test section:

```powershell
node --test --test-isolation=none
node --check src/index.js
```

- [ ] **Step 8: Update roadmap operational basis**

In `docs/ROADMAP.md`, ensure current basis says:

```text
실행: Ubuntu + systemd 직접 실행
검증: Node built-in test runner, GitHub Actions CI
운영 서버 리소스: 1 vCPU, 1GB RAM 기준으로 설계
```

Remove statements that present Docker Compose or Docker build as official current operation.

- [ ] **Step 9: Verify docs are readable and Docker-free**

Run:

```powershell
rg -n "Docker 실행|docker compose|docker build|Docker Compose" README.md docs/OPERATIONS.md docs/ROADMAP.md
```

Expected:
- No official run instructions mention Docker.
- If Docker appears, it is only in a sentence saying Docker is not official or must not run on the server.

- [ ] **Step 10: User commit checkpoint**

Suggested commit message:

```text
docs: document ubuntu systemd operations
```

Do not commit automatically; report the suggested message to the user.

---

### Task 5: Final Verification

**Files:**
- Verify all changed files.

- [ ] **Step 1: Verify changed file list**

Run:

```powershell
git status --short --untracked-files=all
```

Expected changed files include:

```text
M  .github/workflows/ci.yml
M  .env.example
M  README.md
M  docs/OPERATIONS.md
M  docs/ROADMAP.md
A  package-lock.json
A  ops/systemd/kbo-discord-bot.service
A  ops/mariadb/60-kbo-small.cnf
A  ops/deploy-restart-only.sh
D  Dockerfile
D  docker-compose.yml
```

Existing document changes from the roadmap/spec workflow may also be present if not yet committed.

- [ ] **Step 2: Run whitespace check**

Run:

```powershell
git diff --check
```

Expected:
- Exit 0.
- No trailing whitespace errors.

- [ ] **Step 3: Run npm locked install and checks**

Run:

```powershell
npm ci
npm run check
npm test
```

Expected:
- `npm ci` exits 0.
- `npm run check` exits 0.
- `npm test` exits 0 with all tests passing.

- [ ] **Step 4: Confirm CI no longer references Docker**

Run:

```powershell
rg -n "docker|Docker|compose" .github README.md docs/OPERATIONS.md
```

Expected:
- `.github/workflows/ci.yml` has no Docker references.
- README has no Docker run section.
- `docs/OPERATIONS.md` only mentions Docker in the policy that server-side Docker/build is not used.

- [ ] **Step 5: User final commit checkpoint**

Suggested commit message:

```text
ops: switch official runtime to systemd
```

Do not commit automatically; report the suggested message to the user.
