#!/usr/bin/env bash
# FanPitch — one-shot deploy: sync local code + restart docker stack on EC2.
#
# Use this from your laptop AFTER `setup_aws_sandbox.sh` has been run once.
# It assumes:
#   - You're on the branch you want to deploy (typically `main`).
#   - You've committed everything you want shipped (push is OPTIONAL —
#     this script rsyncs the working tree, not the GitHub HEAD).
#   - The EC2 is reachable via the .pem in deploy/artifacts/.
#
# What it does:
#   1. Show what's being deployed (branch + last commit).
#   2. Confirm with you (unless --yes).
#   3. rsync local working tree → EC2.
#   4. scp .env.prod → EC2.
#   5. Rebuild + restart docker-compose stack on EC2.
#   6. Run migrations + demo_setup (idempotent).
#   7. Health-check the live API.
#
# Usage:
#   bash deploy/deploy.sh                       # interactive
#   bash deploy/deploy.sh --yes                 # non-interactive
#   bash deploy/deploy.sh --yes --skip-migrate  # don't re-migrate (faster)

set -euo pipefail
cd "$(dirname "$0")/.."

YES="no"
SKIP_MIGRATE="no"
for arg in "$@"; do
  case "$arg" in
    --yes|-y)         YES="yes" ;;
    --skip-migrate)   SKIP_MIGRATE="yes" ;;
    *)                echo "Unknown arg: $arg"; exit 1 ;;
  esac
done

ARTIFACTS="deploy/artifacts"
if [[ ! -f "$ARTIFACTS/SUMMARY.txt" ]]; then
  echo "✗ Missing $ARTIFACTS/SUMMARY.txt — run deploy/setup_aws_sandbox.sh first." >&2
  exit 1
fi

EC2_DNS=$(grep "EC2 Public DNS:" "$ARTIFACTS/SUMMARY.txt" | awk '{print $4}')
KEY="$ARTIFACTS/fanpitch-sandbox-key.pem"
SSH_OPTS=(-i "$KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15)

C_BLU="\033[1;34m"; C_GRN="\033[1;32m"; C_YEL="\033[1;33m"; C_RED="\033[1;31m"; C_END="\033[0m"
log()  { printf "${C_BLU}▶${C_END} %s\n" "$*"; }
ok()   { printf "${C_GRN}✓${C_END} %s\n" "$*"; }
warn() { printf "${C_YEL}!${C_END} %s\n" "$*"; }
err()  { printf "${C_RED}✗${C_END} %s\n" "$*" >&2; }

# ─── 1. Show what's about to ship ────────────────────────────────────
BRANCH=$(git rev-parse --abbrev-ref HEAD)
COMMIT=$(git rev-parse --short HEAD)
SUBJECT=$(git log -1 --pretty=%s)
DIRTY=$(git status --porcelain | wc -l | tr -d ' ')

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  About to deploy to AWS"
echo "  ─────────────────────"
echo "  Branch  : $BRANCH"
echo "  Commit  : $COMMIT  ($SUBJECT)"
echo "  Target  : ec2-user@$EC2_DNS"
[[ "$DIRTY" -gt 0 ]] && warn "$DIRTY uncommitted change(s) WILL BE SHIPPED — rsync syncs the working tree, not the commit."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [[ "$YES" != "yes" ]]; then
  read -p "Deploy? [y/N] " ANSWER
  [[ "$ANSWER" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
fi

# ─── 2. rsync working tree ───────────────────────────────────────────
log "Syncing local code → ec2-user@$EC2_DNS:/home/ec2-user/fanpitch-api/ ..."
rsync -avz --delete \
  --exclude='.git/' --exclude='.venv/' --exclude='venv/' \
  --exclude='__pycache__/' --exclude='*.pyc' \
  --exclude='.idea/' --exclude='.vscode/' --exclude='.DS_Store' \
  --exclude='mediafiles/' --exclude='staticfiles/' \
  --exclude='deploy/artifacts/' --exclude='*.log' \
  -e "ssh ${SSH_OPTS[*]}" \
  ./ "ec2-user@$EC2_DNS:/home/ec2-user/fanpitch-api/" > /tmp/rsync.log
ok "Code synced ($(grep -c '^' /tmp/rsync.log) files)."

# ─── 3. Push .env ────────────────────────────────────────────────────
log "Pushing .env.prod ..."
scp "${SSH_OPTS[@]}" "$ARTIFACTS/.env.prod" \
    "ec2-user@$EC2_DNS:/home/ec2-user/fanpitch-api/.env" > /dev/null
ok ".env pushed."

# ─── 4. Rebuild + restart ────────────────────────────────────────────
log "Rebuilding Docker images and restarting stack ..."
ssh "${SSH_OPTS[@]}" "ec2-user@$EC2_DNS" \
  'cd /home/ec2-user/fanpitch-api && sudo docker compose -f docker-compose.prod.yml up -d --build' \
  > /tmp/compose.log 2>&1 || { err "docker compose failed — see /tmp/compose.log"; exit 1; }
ok "Stack restarted."

# ─── 5. Migrations ───────────────────────────────────────────────────
if [[ "$SKIP_MIGRATE" != "yes" ]]; then
  log "Waiting 10s for web to settle, then running migrations ..."
  sleep 10
  ssh "${SSH_OPTS[@]}" "ec2-user@$EC2_DNS" \
    'cd /home/ec2-user/fanpitch-api && sudo docker compose -f docker-compose.prod.yml exec -T web python manage.py migrate --noinput' \
    | tail -3
  ok "Migrations applied."
fi

# ─── 6. Health check ─────────────────────────────────────────────────
log "Health check ..."
sleep 3
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://$EC2_DNS/api/docs/" || echo "000")
if [[ "$HTTP_CODE" == "200" ]]; then
  ok "API live → http://$EC2_DNS/api/docs/"
else
  err "API returned HTTP $HTTP_CODE — check: ssh $EC2_DNS 'sudo docker compose -f /home/ec2-user/fanpitch-api/docker-compose.prod.yml logs --tail=50 web'"
  exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ok "Deployed $COMMIT from $BRANCH → http://$EC2_DNS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
