# Discord.js Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the KBO Discord bot runtime from Python `discord.py` to Node.js `discord.js` while preserving schedule, standings, score, team summary, and live score crawling behavior.

**Architecture:** The Node app runs through `src/index.js`, registers guild slash commands with `discord.js`, stores data in MariaDB through `mysql2/promise`, and keeps crawling isolated in service modules. KBO scoreboard parsing and live score refresh stay testable without Discord or DB dependencies.

**Tech Stack:** Node.js, `discord.js` v14, `mysql2`, `puppeteer-core`, MariaDB, Node built-in `node:test`.

---

### Task 1: Node Project Scaffold

**Files:**
- Create: `package.json`
- Create: `src/config.js`
- Create: `src/constants.js`
- Modify: `.gitignore`

- [ ] **Step 1: Add Node package metadata**

Create `package.json` with `type: "module"`, `start`, `test`, and `check` scripts. Runtime dependencies are `discord.js`, `mysql2`, and `puppeteer-core`.

- [ ] **Step 2: Add config loader**

Create `src/config.js` to read environment variables first and optionally fall back to `config.json` for existing local setups.

- [ ] **Step 3: Add shared constants**

Create `src/constants.js` for KST timezone helpers, weekdays, rank emoji, and team logo emoji mapping.

- [ ] **Step 4: Verify scaffold**

Run: `node --test`

Expected: no tests found or PASS once tests are added.

### Task 2: Testable Score Utilities

**Files:**
- Create: `src/services/liveScore.js`
- Create: `src/utils/formatters.js`
- Create: `test/liveScore.test.js`
- Create: `test/formatters.test.js`

- [ ] **Step 1: Write parser tests**

Test that one `smsScore` block produces `gameDate`, `gameId`, teams, scores, status, stadium, and time.

- [ ] **Step 2: Implement parser and formatters**

Implement `parseScoreboardGames`, `liveGameStatus`, `formatScoreLine`, `formatScheduleMatchup`, and team matching helpers.

- [ ] **Step 3: Verify**

Run: `node --test`

Expected: parser and formatter tests PASS.

### Task 3: Database and Crawling Services

**Files:**
- Create: `src/services/database.js`
- Create: `src/services/kboCrawler.js`
- Create: `src/services/dataReady.js`

- [ ] **Step 1: Port schema and DB methods**

Implement `ensureSchema`, `hasStandingsData`, `hasScheduleDataForDate`, `selectStandings`, `selectGamesAndScores`, `upsertStandings`, `upsertGameAndScore`, and `updateLiveGameScore`.

- [ ] **Step 2: Port KBO crawling**

Implement standings and schedule refresh with `puppeteer-core`, and live score refresh with KBO scoreboard plus mobile `GetGameState`.

- [ ] **Step 3: Port data readiness policy**

Implement schedule cache guard, standings refresh-on-command, and live score refresh only during today's active game window.

### Task 4: Discord.js Commands and Runtime

**Files:**
- Create: `src/commands/kboCommands.js`
- Create: `src/index.js`
- Modify: `Dockerfile`
- Modify: `docker-compose.yml`
- Modify: `README.md`

- [ ] **Step 1: Port slash commands**

Register `/순위`, `/성적`, `/일정`, `/스코어`, `/팀`, `/차렷`, `/열중쉬어`, and `/쉬어`.

- [ ] **Step 2: Port bot runtime**

Start the Discord client, register guild commands on ready, run data bootstrap, and schedule the daily 06:00 KST refresh.

- [ ] **Step 3: Switch Docker to Node**

Use a Node slim image, install Chromium for `puppeteer-core`, run `npm install --omit=dev`, and start with `npm start`.

- [ ] **Step 4: Verify syntax and tests**

Run:

```bash
node --test
node --check src/index.js
```

Expected: tests PASS and syntax check exits 0.

### Task 5: Cleanup and Commit

**Files:**
- Remove or retire Python runtime files after Node runtime is complete.
- Keep `.env.example` compatible with the new Node runtime.

- [ ] **Step 1: Remove stale Python execution references**

Update docs and Docker so the project no longer tells users to run `python kbo.py`.

- [ ] **Step 2: Commit migration**

Use existing commit style:

```bash
git add .
git commit -m "feat: migrate bot to discord.js"
```
