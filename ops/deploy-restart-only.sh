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
