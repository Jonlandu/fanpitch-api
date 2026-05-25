#!/usr/bin/env bash
# FanPitch — DESTROY all sandbox resources (run before lease expires to avoid bill).
#
# DANGER: this deletes EVERYTHING. There is no undo.
# Requires the same AWS profile as setup_aws_sandbox.sh.
#
# USAGE: AWS_PROFILE=fanpitch-sandbox bash deploy/teardown_aws_sandbox.sh

set -euo pipefail

REGION="${AWS_REGION:-eu-central-1}"
KEY_NAME="${KEY_NAME:-fanpitch-sandbox-key}"
SG_NAME="${SG_NAME:-fanpitch-sg}"
ROLE_NAME="${ROLE_NAME:-FanPitchAppRole}"
INSTANCE_PROFILE_NAME="${INSTANCE_PROFILE_NAME:-FanPitchAppRole}"
DB_INSTANCE_ID="${DB_INSTANCE_ID:-fanpitch-db}"
EC2_NAME_TAG="${EC2_NAME_TAG:-fanpitch-web}"

C_RED="\033[1;31m"; C_GREEN="\033[1;32m"; C_END="\033[0m"
log() { echo -e "${C_RED}✗${C_END} $*"; }
ok()  { echo -e "${C_GREEN}✓${C_END} $*"; }

echo -e "${C_RED}This will DELETE: EC2, RDS, S3 bucket contents, IAM role, security group, key pair.${C_END}"
read -p "Type 'destroy' to confirm: " CONFIRM
[[ "$CONFIRM" == "destroy" ]] || { echo "Aborted."; exit 0; }

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
S3_BUCKET="${S3_BUCKET:-fanpitch-media-$ACCOUNT_ID}"

log "Terminating EC2 instances tagged $EC2_NAME_TAG ..."
INSTANCE_IDS=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=$EC2_NAME_TAG" "Name=instance-state-name,Values=pending,running,stopping,stopped" --query "Reservations[].Instances[].InstanceId" --output text --region "$REGION" || echo "")
if [[ -n "$INSTANCE_IDS" ]]; then
  aws ec2 terminate-instances --instance-ids $INSTANCE_IDS --region "$REGION" >/dev/null
  aws ec2 wait instance-terminated --instance-ids $INSTANCE_IDS --region "$REGION"
  ok "EC2 terminated."
fi

log "Deleting RDS instance $DB_INSTANCE_ID ..."
aws rds delete-db-instance --db-instance-identifier "$DB_INSTANCE_ID" --skip-final-snapshot --delete-automated-backups --region "$REGION" 2>/dev/null || true

log "Emptying and deleting S3 bucket $S3_BUCKET ..."
aws s3 rm "s3://$S3_BUCKET" --recursive --region "$REGION" 2>/dev/null || true
aws s3api delete-bucket --bucket "$S3_BUCKET" --region "$REGION" 2>/dev/null || true
ok "S3 bucket gone."

log "Deleting security group $SG_NAME ..."
SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$SG_NAME" --query "SecurityGroups[0].GroupId" --output text --region "$REGION" 2>/dev/null || echo "")
[[ -n "$SG_ID" && "$SG_ID" != "None" ]] && aws ec2 delete-security-group --group-id "$SG_ID" --region "$REGION" 2>/dev/null || true

log "Deleting key pair $KEY_NAME ..."
aws ec2 delete-key-pair --key-name "$KEY_NAME" --region "$REGION" 2>/dev/null || true

log "Detaching and deleting IAM role $ROLE_NAME + instance profile ..."
aws iam remove-role-from-instance-profile --instance-profile-name "$INSTANCE_PROFILE_NAME" --role-name "$ROLE_NAME" 2>/dev/null || true
aws iam delete-instance-profile --instance-profile-name "$INSTANCE_PROFILE_NAME" 2>/dev/null || true
for POLICY in FanPitchS3Access FanPitchBedrockInvoke; do
  aws iam delete-role-policy --role-name "$ROLE_NAME" --policy-name "$POLICY" 2>/dev/null || true
done
aws iam detach-role-policy --role-name "$ROLE_NAME" --policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy 2>/dev/null || true
aws iam delete-role --role-name "$ROLE_NAME" 2>/dev/null || true

log "Removing local artifacts ..."
rm -rf "$(dirname "$0")/artifacts"

ok "Tear-down complete. Verify in the AWS console that nothing is left."
