#!/bin/bash
set -euo pipefail

SSH_OPTIONS=("$@")

# Build the project
bun run build

# Deploy Trigger.dev tasks (uses TRIGGER_ACCESS_TOKEN for CLI auth)
TRIGGER_ACCESS_TOKEN="$TRIGGER_DEPLOY_KEY" bunx trigger deploy

timestamp=$(date +%s)
DEPLOY_DIR="/var/www/api.metro-boulot.photos"

# Create target directory with proper permissions
ssh "${SSH_OPTIONS[@]}" root@167.71.143.97 "mkdir -p ${DEPLOY_DIR}-${timestamp} && chmod 755 ${DEPLOY_DIR}-${timestamp}"

# Deploy the built files and data
scp "${SSH_OPTIONS[@]}" -r dist/* root@167.71.143.97:${DEPLOY_DIR}-${timestamp}/
scp "${SSH_OPTIONS[@]}" -r data root@167.71.143.97:${DEPLOY_DIR}-${timestamp}/
scp "${SSH_OPTIONS[@]}" package.json bun.lock root@167.71.143.97:${DEPLOY_DIR}-${timestamp}/

# Copy production env file
if [ -f .env.production ]; then
    echo "Copying production env file..."
    # If S3_SECRET_ACCESS_KEY is in the shell env, then use it to update .env.production
    if [ -n "$S3_SECRET_ACCESS_KEY" ]; then
        echo "S3_SECRET_ACCESS_KEY found in shell env, updating .env.production..."
        sed -i "s/S3_SECRET_ACCESS_KEY=.*/S3_SECRET_ACCESS_KEY=$S3_SECRET_ACCESS_KEY/" .env.production
    fi
    if [ -n "$TRIGGER_API_KEY" ]; then
        echo "TRIGGER_API_KEY found in shell env, updating .env.production..."
        sed -i "s/TRIGGER_SECRET_KEY=.*/TRIGGER_SECRET_KEY=$TRIGGER_API_KEY/" .env.production
    fi
    scp "${SSH_OPTIONS[@]}" .env.production root@167.71.143.97:${DEPLOY_DIR}-${timestamp}/.env
fi

# Install production dependencies and update symlink
ssh "${SSH_OPTIONS[@]}" root@167.71.143.97 "cd ${DEPLOY_DIR}-${timestamp} && bun install --frozen-lockfile --production"

# Create a new symlink (remove old one if exists)
ssh "${SSH_OPTIONS[@]}" root@167.71.143.97 "rm -f ${DEPLOY_DIR} && ln -s ${DEPLOY_DIR}-${timestamp} ${DEPLOY_DIR}"

# Restart the backend service with PM2
ssh "${SSH_OPTIONS[@]}" root@167.71.143.97 "cd ${DEPLOY_DIR} && pm2 delete metro-api 2>/dev/null || true && pm2 start index.js --name metro-api --interpreter bun"

# Clean up old deployments, keep the 3 most recent
ssh "${SSH_OPTIONS[@]}" root@167.71.143.97 'ls -dt /var/www/api.metro-boulot.photos-* | tail -n +4 | xargs rm -rf --'

echo "Backend deployed! Make sure PM2 is set to start on boot: pm2 startup && pm2 save"
