#!/bin/bash
# Uploads the already-built dist/ (CI builds with VITE_API_URL in an earlier step, before the SSH key is
# loaded), swaps the live symlink and keeps the 3 latest deploys.
set -euo pipefail

SERVER="${DEPLOY_USER:-root}@${DEPLOY_HOST:-167.71.143.97}"
BASE="/var/www/metro-boulot.photos"
timestamp=$(date +%s)

[ -d dist ] || { echo "dist/ not found: build first" >&2; exit 1; }

ssh "$SERVER" "mkdir -p ${BASE}-${timestamp} && chmod 755 ${BASE}-${timestamp}"
scp -r dist/* "$SERVER:${BASE}-${timestamp}/"
ssh "$SERVER" "ln -sfn ${BASE}-${timestamp} ${BASE}"
ssh "$SERVER" "ls -d ${BASE}-[0-9]* | sort -t- -k2 -n | head -n -3 | xargs -r -t rm -rf --"
