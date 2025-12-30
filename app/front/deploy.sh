#!/bin/bash

SSH_OPTIONS="$@"

# Build the project
npm run build

timestamp=$(date +%s)

# Create target directory with proper permissions
ssh $SSH_OPTIONS root@167.71.143.97 "mkdir -p /var/www/metro-boulot.photos-${timestamp} && chmod 755 /var/www/metro-boulot.photos-${timestamp}"

# Deploy the project
scp $SSH_OPTIONS -r dist/* root@167.71.143.97:/var/www/metro-boulot.photos-${timestamp}/
scp $SSH_OPTIONS package*.json root@167.71.143.97:/var/www/metro-boulot.photos-${timestamp}/

# Install dependencies
ssh $SSH_OPTIONS root@167.71.143.97 "cd /var/www/metro-boulot.photos-${timestamp} && npm i --omit=dev"

# Create a new symlink
ssh $SSH_OPTIONS root@167.71.143.97 "(rm /var/www/metro-boulot.photos || true) && ln -s /var/www/metro-boulot.photos-${timestamp} /var/www/metro-boulot.photos"
