#!/bin/bash

SSH_OPTIONS="$@"

# Set production API URL and build
VITE_API_URL=https://api.metro-boulot.photos npm run build

timestamp=$(date +%s)

# Create target directory with proper permissions
ssh $SSH_OPTIONS root@167.71.143.97 "mkdir -p /var/www/metro-boulot.photos-${timestamp} && chmod 755 /var/www/metro-boulot.photos-${timestamp}"

# Deploy the built static files
scp $SSH_OPTIONS -r dist/* root@167.71.143.97:/var/www/metro-boulot.photos-${timestamp}/

# Create a new symlink (remove old one if exists)
ssh $SSH_OPTIONS root@167.71.143.97 "rm -f /var/www/metro-boulot.photos && ln -s /var/www/metro-boulot.photos-${timestamp} /var/www/metro-boulot.photos"
