# AGENTS.md

## Project shape
- Runtime is now plain JavaScript on `discord.js`; `index.js` is the bot entrypoint and Docker `CMD` runs `node index.js`.
- Slash commands live in `commands/*.js`; `deploy-commands.js` registers guild commands through the Discord REST API.
- Core JS boundaries: `src/config.js` loads `.env`, `src/database.js` owns MariaDB schema/queries, `src/crawler/kboCrawler.js` owns Selenium scraping, and `src/render/` owns Discord output formatting.
- Legacy Python files (`kbo.py`, `database.py`, `settings.py`, `kbo_crawler.py`) are still present as migration references and guard-test sources; do not treat them as the primary runtime unless explicitly asked.

## Commands that matter
- Install/update JS dependencies: `npm install`; Docker uses `npm ci --omit=dev`, so keep `package-lock.json` committed.
- JS verification baseline: `npm run check` (`node --check index.js`, `node --check deploy-commands.js`, and `node --test`).
- Register slash commands after changing `commands/*.js`: `npm run deploy:commands` with valid `DISCORD_TOKEN`, `DISCORD_CLIENT_ID`, and `DISCORD_GUILD_ID`.
- Container run: `cp .env.example .env`, fill secrets/DB values, then `docker compose up -d --build`; inspect with `docker compose ps` and `docker compose logs -f bot`.
- Python guard tests may still be useful during migration, but local Python 3.9 fails some existing tests because they use Python 3.10+ `X | Y` annotation syntax.

## Runtime/config gotchas
- `.env.example` must include `DISCORD_CLIENT_ID`; `deploy-commands.js` needs application/client ID separately from guild/channel IDs.
- `src/config.js` reads environment variables via `dotenv`; Compose also supplies `.env` via `env_file`.
- `src/config.js` keeps legacy `MARIA_*` fallbacks for DB settings and defaults `DB_HOST` to `127.0.0.1` outside Compose.
- Docker installs Chromium/ChromeDriver because `src/crawler/kboCrawler.js` uses `selenium-webdriver`; keep `driver.quit()` in `finally` blocks when editing crawler entrypoints.
- Running the real bot needs valid Discord token/client/guild IDs, reachable MariaDB, Chromium/ChromeDriver, and network access to Discord plus KBO/Naver sports sites.

## Migration invariants
- Standings row contract remains `[id, team, win, lose, draw, rate, last_10, streak, home, away]`.
- Schedule/game score contract remains `[id, time, away, away_score, home_score, home, stadium, remarks]`.
- Schedule scores use `-1` as the no-score sentinel and render as `vs` when appropriate; JS tests in `test/render.test.js` protect this.
- Daily schedule refresh should use KST helpers from `src/time.js`; avoid host-local date logic for crawler refresh.
- Keep command names and Korean response text compatible with the old bot unless the user asks for UX changes.

## Workflow notes
- Existing workflow doc is `PLAN_FIRST_WORKFLOW.md`: plan first, work on `rebuilding-planning`, commit only after the phase-specific verification passes, and keep each commit to one phase/independent task.
- Do not add Sisyphus as a co-worker/collaborator in repo rules or workflow docs.
- There is no CI workflow or pre-commit config in the repo; run the relevant local verification command before reporting completion.
- `.env` is ignored by Docker context and should stay uncommitted; use `.env.example` for variable names only.
