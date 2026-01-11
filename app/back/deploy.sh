#!/bin/bash

SSH_OPTIONS="$@"

# Build the project
npm run build

timestamp=$(date +%s)
DEPLOY_DIR="/var/www/api.metro-boulot.photos"

# Create target directory with proper permissions
ssh $SSH_OPTIONS root@167.71.143.97 "mkdir -p ${DEPLOY_DIR}-${timestamp} && chmod 755 ${DEPLOY_DIR}-${timestamp}"

# Deploy the built files and data
scp $SSH_OPTIONS -r dist/* root@167.71.143.97:${DEPLOY_DIR}-${timestamp}/
scp $SSH_OPTIONS -r data root@167.71.143.97:${DEPLOY_DIR}-${timestamp}/
scp $SSH_OPTIONS package.json package-lock.json root@167.71.143.97:${DEPLOY_DIR}-${timestamp}/

# Copy production env file
if [ -f .env.production ]; then
    scp $SSH_OPTIONS .env.production root@167.71.143.97:${DEPLOY_DIR}-${timestamp}/.env
fi

# Install production dependencies and update symlink
ssh $SSH_OPTIONS root@167.71.143.97 "cd ${DEPLOY_DIR}-${timestamp} && npm ci --production"

# Create a new symlink (remove old one if exists)
ssh $SSH_OPTIONS root@167.71.143.97 "rm -f ${DEPLOY_DIR} && ln -s ${DEPLOY_DIR}-${timestamp} ${DEPLOY_DIR}"

# Restart the backend service with PM2
ssh $SSH_OPTIONS root@167.71.143.97 "cd ${DEPLOY_DIR} && pm2 delete metro-api 2>/dev/null || true && pm2 start index.js --name metro-api"

echo "Backend deployed! Make sure PM2 is set to start on boot: pm2 startup && pm2 save"
