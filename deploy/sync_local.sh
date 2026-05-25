#!/usr/bin/env bash
# FanPitch — rsync the local working tree to the EC2 host.
#
# Use this INSTEAD of git clone when:
#   - the latest commits aren't pushed to GitHub yet (user reserves push)
#   - you want to iterate fast without a push/pull cycle
#
# Prereqs: deploy/setup_aws_sandbox.sh has run (artifacts/SUMMARY.txt exists)
#
# Usage:  bash deploy/sync_local.sh
#         bash deploy/sync_local.sh --restart   # also restart docker stack after sync

set -euo pipefail

cd "$(dirname "$0")/.."   # fanpitch-api repo root

ARTIFACTS="deploy/artifacts"
if [[ ! -f "$ARTIFACTS/SUMMARY.txt" ]]; then
  echo "✗ No deploy artifacts found. Run deploy/setup_aws_sandbox.sh first." >&2
  exit 1
fi

EC2_DNS=$(grep "EC2 Public DNS:" "$ARTIFACTS/SUMMARY.txt" | awk '{print $4}')
KEY="$ARTIFACTS/fanpitch-sandbox-key.pem"

if [[ -z "$EC2_DNS" || ! -f "$KEY" ]]; then
  echo "✗ Could not read EC2_DNS or key file from artifacts/." >&2
  exit 1
fi

echo "▶ Syncing local code → ec2-user@$EC2_DNS:/home/ec2-user/fanpitch-api/ …"
rsync -avz --delete \
  --exclude='.git/' \
  --exclude='.venv/' \
  --exclude='venv/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='.idea/' \
  --exclude='.vscode/' \
  --exclude='.DS_Store' \
  --exclude='mediafiles/' \
  --exclude='staticfiles/' \
  --exclude='deploy/artifacts/' \
  --exclude='*.log' \
  -e "ssh -i $KEY -o StrictHostKeyChecking=no" \
  ./ "ec2-user@$EC2_DNS:/home/ec2-user/fanpitch-api/"

echo "✓ Sync complete."

if [[ "${1:-}" == "--restart" ]]; then
  echo "▶ Pushing .env (if updated) and restarting docker stack …"
  scp -i "$KEY" -o StrictHostKeyChecking=no \
    "$ARTIFACTS/.env.prod" "ec2-user@$EC2_DNS:/home/ec2-user/fanpitch-api/.env"
  ssh -i "$KEY" -o StrictHostKeyChecking=no "ec2-user@$EC2_DNS" \
    'cd /home/ec2-user/fanpitch-api && sudo docker compose -f docker-compose.prod.yml up -d --build && sudo docker compose -f docker-compose.prod.yml exec -T web python manage.py migrate --noinput'
  echo "✓ Stack restarted with latest code."
fi
