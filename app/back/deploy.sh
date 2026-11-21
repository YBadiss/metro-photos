#!/bin/bash
# Uploads the already-built dist/ (CI builds, migrates and deploys Trigger.dev tasks in an earlier step,
# before the SSH key is loaded), writes the production .env, installs runtime deps on the droplet and
# (re)starts the API under PM2.
set -euo pipefail

SERVER="${DEPLOY_USER:-root}@${DEPLOY_HOST:-167.71.143.97}"
timestamp=$(date +%s)
DEPLOY_DIR="/var/www/api.metro-boulot.photos"
DIR="${DEPLOY_DIR}-${timestamp}"

[ -d dist ] || { echo "dist/ not found: run bun run build first" >&2; exit 1; }

ssh "$SERVER" "mkdir -p $DIR && chmod 755 $DIR"
scp -r dist/* package.json bun.lock "$SERVER:$DIR/"

# Production env: committed .env.production with secrets filled in from the CI environment.
env_file=$(mktemp)
trap 'rm -f "$env_file"' EXIT
cp .env.production "$env_file"
[ -n "${S3_SECRET_ACCESS_KEY:-}" ] && sed -i "s|^S3_SECRET_ACCESS_KEY=.*|S3_SECRET_ACCESS_KEY=$S3_SECRET_ACCESS_KEY|" "$env_file"
[ -n "${TRIGGER_API_KEY:-}" ] && sed -i "s|^TRIGGER_SECRET_KEY=.*|TRIGGER_SECRET_KEY=$TRIGGER_API_KEY|" "$env_file"
[ -n "${DATABASE_URL:-}" ] && sed -i "s|^DATABASE_URL=.*|DATABASE_URL=$DATABASE_URL|" "$env_file"
scp "$env_file" "$SERVER:$DIR/.env"
ssh "$SERVER" "chmod 600 $DIR/.env"

ssh "$SERVER" "cd $DIR && bun install --frozen-lockfile --production"
ssh "$SERVER" "ln -sfn $DIR $DEPLOY_DIR"

# Start from the new directory and `pm2 save`, so the process comes back after a reboot.
ssh "$SERVER" "pm2 delete metro-api >/dev/null 2>&1 || true; cd $DIR && pm2 start index.js --name metro-api --interpreter bun && pm2 save"

# Keep the 3 most recent deploys
ssh "$SERVER" "ls -d ${DEPLOY_DIR}-[0-9]* | sort -t- -k2 -n | head -n -3 | xargs -r -t rm -rf --"
