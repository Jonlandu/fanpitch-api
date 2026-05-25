#!/usr/bin/env bash
# FanPitch — provision the AWS Innovation Sandbox resources.
#
# WHAT THIS DOES (in order, idempotent — safe to re-run):
#   1. Verify AWS CLI credentials and we are in eu-central-1
#   2. Create S3 bucket for user-uploaded media (with CORS + lifecycle)
#   3. Create RDS PostgreSQL db.t4g.micro (single AZ, public-accessible)
#   4. Create EC2 key-pair + Security Group + IAM Role/Instance-Profile
#   5. Launch EC2 t2.micro with Amazon Linux 2023
#   6. Set up billing alarms at $30/$40/$45
#   7. Print everything you need to SSH in and finish bootstrapping
#
# PREREQS:
#   - aws cli v2 configured with sandbox credentials (profile: fanpitch-sandbox)
#   - Bedrock Claude 3 Haiku model access granted in the console (eu-central-1)
#
# USAGE:
#   AWS_PROFILE=fanpitch-sandbox bash deploy/setup_aws_sandbox.sh
#
# DURATION: ~6 min (RDS create is the slow step)

set -euo pipefail

# ─── Configuration ───────────────────────────────────────────────────
REGION="${AWS_REGION:-eu-central-1}"
PROJECT_TAG="fanpitch"
KEY_NAME="${KEY_NAME:-fanpitch-sandbox-key}"
SG_NAME="${SG_NAME:-fanpitch-sg}"
ROLE_NAME="${ROLE_NAME:-FanPitchAppRole}"
INSTANCE_PROFILE_NAME="${INSTANCE_PROFILE_NAME:-FanPitchAppRole}"
DB_INSTANCE_ID="${DB_INSTANCE_ID:-fanpitch-db}"
DB_USER="${DB_USER:-fanpitch}"
EC2_INSTANCE_TYPE="${EC2_INSTANCE_TYPE:-t2.micro}"
EC2_NAME_TAG="${EC2_NAME_TAG:-fanpitch-web}"

# Colors
C_GREEN="\033[1;32m"; C_YEL="\033[1;33m"; C_RED="\033[1;31m"; C_BLU="\033[1;34m"; C_DIM="\033[2m"; C_END="\033[0m"
log()  { echo -e "${C_BLU}▶${C_END} $*"; }
ok()   { echo -e "${C_GREEN}✓${C_END} $*"; }
warn() { echo -e "${C_YEL}!${C_END} $*"; }
err()  { echo -e "${C_RED}✗${C_END} $*" >&2; }

# ─── 1. Pre-flight ───────────────────────────────────────────────────
log "Pre-flight: verifying AWS CLI credentials in $REGION ..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || true)
if [[ -z "$ACCOUNT_ID" ]]; then
  err "AWS CLI not configured. Run: aws configure --profile fanpitch-sandbox"
  exit 1
fi
ok "Account: $ACCOUNT_ID  |  Region: $REGION"

S3_BUCKET="${S3_BUCKET:-fanpitch-media-$ACCOUNT_ID}"
ARTIFACTS_DIR="$(cd "$(dirname "$0")" && pwd)/artifacts"
mkdir -p "$ARTIFACTS_DIR"

# Strong random password for the DB master user
if [[ -f "$ARTIFACTS_DIR/db_password.txt" ]]; then
  DB_PASSWORD=$(cat "$ARTIFACTS_DIR/db_password.txt")
  warn "Reusing existing DB password from artifacts/db_password.txt"
else
  DB_PASSWORD=$(python3 -c 'import secrets,string;print("".join(secrets.choice(string.ascii_letters+string.digits) for _ in range(32)))')
  echo "$DB_PASSWORD" > "$ARTIFACTS_DIR/db_password.txt"
  chmod 600 "$ARTIFACTS_DIR/db_password.txt"
  ok "Generated DB password (saved to artifacts/db_password.txt — keep it safe!)"
fi

# ─── 2. S3 bucket for user media ─────────────────────────────────────
log "Creating S3 bucket: s3://$S3_BUCKET ..."
if aws s3api head-bucket --bucket "$S3_BUCKET" --region "$REGION" 2>/dev/null; then
  ok "Bucket already exists."
else
  aws s3api create-bucket \
    --bucket "$S3_BUCKET" \
    --region "$REGION" \
    --create-bucket-configuration LocationConstraint="$REGION" \
    >/dev/null
  ok "Bucket created."
fi

log "Configuring CORS on bucket ..."
aws s3api put-bucket-cors --bucket "$S3_BUCKET" --region "$REGION" --cors-configuration '{
  "CORSRules":[{
    "AllowedHeaders":["*"],
    "AllowedMethods":["PUT","GET","HEAD"],
    "AllowedOrigins":["*"],
    "ExposeHeaders":["ETag"],
    "MaxAgeSeconds":3000
  }]
}'
ok "CORS configured."

log "Configuring lifecycle (uploads/ → expire after 30d) ..."
# STANDARD_IA transition requires min 30d, which is when we expire anyway,
# so just expire — no point transitioning the day before deletion.
aws s3api put-bucket-lifecycle-configuration --bucket "$S3_BUCKET" --region "$REGION" --lifecycle-configuration '{
  "Rules":[{
    "ID":"uploads-cleanup",
    "Status":"Enabled",
    "Filter":{"Prefix":"uploads/"},
    "Expiration":{"Days":30}
  }]
}'
ok "Lifecycle configured."

log "Blocking public ACLs (security baseline) ..."
aws s3api put-public-access-block --bucket "$S3_BUCKET" --region "$REGION" \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
ok "Public access blocked."

aws s3api put-bucket-tagging --bucket "$S3_BUCKET" --region "$REGION" \
  --tagging "TagSet=[{Key=project,Value=$PROJECT_TAG}]" >/dev/null

# ─── 3. RDS PostgreSQL ───────────────────────────────────────────────
log "Ensuring default VPC + DB subnet group exist ..."
DEFAULT_VPC=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region "$REGION" 2>/dev/null || echo "None")
if [[ "$DEFAULT_VPC" == "None" || -z "$DEFAULT_VPC" ]]; then
  log "No default VPC — creating one ..."
  aws ec2 create-default-vpc --region "$REGION" >/dev/null
  sleep 5
fi
DB_SUBNET_GROUP="fanpitch-db-subnets"
if ! aws rds describe-db-subnet-groups --db-subnet-group-name "$DB_SUBNET_GROUP" --region "$REGION" >/dev/null 2>&1; then
  SUBNETS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text --region $REGION)" --query "Subnets[].SubnetId" --output text --region "$REGION")
  aws rds create-db-subnet-group --db-subnet-group-name "$DB_SUBNET_GROUP" \
    --db-subnet-group-description "FanPitch default VPC subnets" \
    --subnet-ids $SUBNETS --tags Key=project,Value=$PROJECT_TAG --region "$REGION" >/dev/null
  ok "DB subnet group created."
else
  ok "DB subnet group already exists."
fi

log "Creating RDS PostgreSQL instance: $DB_INSTANCE_ID ..."
if aws rds describe-db-instances --db-instance-identifier "$DB_INSTANCE_ID" --region "$REGION" >/dev/null 2>&1; then
  ok "RDS instance already exists."
else
  aws rds create-db-instance \
    --db-instance-identifier "$DB_INSTANCE_ID" \
    --db-instance-class db.t4g.micro \
    --engine postgres --engine-version 16.6 \
    --allocated-storage 20 \
    --master-username "$DB_USER" \
    --master-user-password "$DB_PASSWORD" \
    --db-subnet-group-name "$DB_SUBNET_GROUP" \
    --backup-retention-period 1 \
    --publicly-accessible \
    --no-multi-az \
    --no-deletion-protection \
    --storage-type gp3 \
    --tags Key=project,Value=$PROJECT_TAG \
    --region "$REGION" \
    >/dev/null
  ok "RDS instance requested (creation takes ~5 min — running other steps in parallel)."
fi

# ─── 4. EC2 key pair, security group, IAM role ───────────────────────
log "Creating EC2 key pair: $KEY_NAME ..."
KEY_FILE="$ARTIFACTS_DIR/$KEY_NAME.pem"
if aws ec2 describe-key-pairs --key-names "$KEY_NAME" --region "$REGION" >/dev/null 2>&1; then
  if [[ ! -f "$KEY_FILE" ]]; then
    warn "Key pair exists in AWS but no local .pem found — you'll have to recreate it."
    aws ec2 delete-key-pair --key-name "$KEY_NAME" --region "$REGION"
    aws ec2 create-key-pair --key-name "$KEY_NAME" --query KeyMaterial --output text --region "$REGION" > "$KEY_FILE"
    chmod 400 "$KEY_FILE"
  else
    ok "Key pair already exists (artifacts/$KEY_NAME.pem)."
  fi
else
  aws ec2 create-key-pair --key-name "$KEY_NAME" --query KeyMaterial --output text --region "$REGION" > "$KEY_FILE"
  chmod 400 "$KEY_FILE"
  ok "Key pair created and saved to artifacts/$KEY_NAME.pem."
fi

log "Creating security group: $SG_NAME ..."
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region "$REGION")
SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$SG_NAME" --query "SecurityGroups[0].GroupId" --output text --region "$REGION" 2>/dev/null || echo "")
if [[ -z "$SG_ID" || "$SG_ID" == "None" ]]; then
  SG_ID=$(aws ec2 create-security-group --group-name "$SG_NAME" --description "FanPitch web + ssh + postgres" --vpc-id "$VPC_ID" --query GroupId --output text --region "$REGION")
  ok "Security group created: $SG_ID"
else
  ok "Security group already exists: $SG_ID"
fi

# Open ingress (re-run is safe; rules return InvalidPermission.Duplicate which we ignore)
for PORT in 22 80 443 8000; do
  aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port "$PORT" --cidr 0.0.0.0/0 --region "$REGION" 2>/dev/null || true
done
# Allow Postgres from the EC2 itself (we'll authorize the EC2's eni later via SG-ref but for now open to SG itself)
aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 5432 --source-group "$SG_ID" --region "$REGION" 2>/dev/null || true
ok "Ingress rules: 22/80/443/8000 open to world; 5432 open within SG."

log "Creating IAM role: $ROLE_NAME ..."
if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  ok "IAM role already exists."
else
  aws iam create-role --role-name "$ROLE_NAME" --assume-role-policy-document '{
    "Version":"2012-10-17",
    "Statement":[{
      "Effect":"Allow",
      "Principal":{"Service":"ec2.amazonaws.com"},
      "Action":"sts:AssumeRole"
    }]
  }' >/dev/null
  ok "IAM role created."
fi

log "Attaching policies (S3, Bedrock, CloudWatch) ..."
cat > "$ARTIFACTS_DIR/s3-bucket-policy.json" <<EOF
{
  "Version":"2012-10-17",
  "Statement":[{
    "Effect":"Allow",
    "Action":["s3:GetObject","s3:PutObject","s3:DeleteObject","s3:ListBucket"],
    "Resource":["arn:aws:s3:::$S3_BUCKET","arn:aws:s3:::$S3_BUCKET/*"]
  }]
}
EOF
aws iam put-role-policy --role-name "$ROLE_NAME" --policy-name "FanPitchS3Access" --policy-document file://"$ARTIFACTS_DIR/s3-bucket-policy.json"

aws iam put-role-policy --role-name "$ROLE_NAME" --policy-name "FanPitchBedrockInvoke" --policy-document '{
  "Version":"2012-10-17",
  "Statement":[{
    "Effect":"Allow",
    "Action":["bedrock:InvokeModel","bedrock:InvokeModelWithResponseStream"],
    "Resource":"*"
  }]
}'

aws iam attach-role-policy --role-name "$ROLE_NAME" --policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy 2>/dev/null || true
ok "Policies attached."

log "Creating instance profile and attaching the role ..."
if aws iam get-instance-profile --instance-profile-name "$INSTANCE_PROFILE_NAME" >/dev/null 2>&1; then
  ok "Instance profile already exists."
else
  aws iam create-instance-profile --instance-profile-name "$INSTANCE_PROFILE_NAME" >/dev/null
  aws iam add-role-to-instance-profile --instance-profile-name "$INSTANCE_PROFILE_NAME" --role-name "$ROLE_NAME"
  ok "Instance profile created."
fi
# Give IAM a moment to propagate (otherwise EC2 launch may fail)
sleep 8

# ─── 5. Launch EC2 ───────────────────────────────────────────────────
log "Looking up latest Amazon Linux 2023 AMI ..."
AMI_ID=$(aws ssm get-parameter --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 --query Parameter.Value --output text --region "$REGION")
ok "AMI: $AMI_ID"

log "Looking for an existing FanPitch EC2 instance ..."
EXISTING=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=$EC2_NAME_TAG" "Name=instance-state-name,Values=pending,running,stopped" --query "Reservations[].Instances[].InstanceId" --output text --region "$REGION")
if [[ -n "$EXISTING" ]]; then
  INSTANCE_ID=$EXISTING
  ok "EC2 already exists: $INSTANCE_ID"
else
  log "Launching EC2 $EC2_INSTANCE_TYPE ..."
  INSTANCE_ID=$(aws ec2 run-instances \
    --image-id "$AMI_ID" \
    --instance-type "$EC2_INSTANCE_TYPE" \
    --key-name "$KEY_NAME" \
    --security-group-ids "$SG_ID" \
    --iam-instance-profile Name="$INSTANCE_PROFILE_NAME" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$EC2_NAME_TAG},{Key=project,Value=$PROJECT_TAG}]" \
    --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":20,"VolumeType":"gp3","DeleteOnTermination":true}}]' \
    --region "$REGION" \
    --query "Instances[0].InstanceId" --output text)
  ok "Instance launching: $INSTANCE_ID"
fi

log "Waiting for EC2 to enter 'running' state ..."
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"

EC2_PUBLIC_DNS=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --query "Reservations[0].Instances[0].PublicDnsName" --output text --region "$REGION")
EC2_PUBLIC_IP=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --query "Reservations[0].Instances[0].PublicIpAddress" --output text --region "$REGION")
ok "EC2 running at: $EC2_PUBLIC_DNS ($EC2_PUBLIC_IP)"

# ─── 6. Wait for RDS to be available ─────────────────────────────────
log "Waiting for RDS to become available (this is the slow step, ~5 min) ..."
aws rds wait db-instance-available --db-instance-identifier "$DB_INSTANCE_ID" --region "$REGION"
RDS_ENDPOINT=$(aws rds describe-db-instances --db-instance-identifier "$DB_INSTANCE_ID" --query "DBInstances[0].Endpoint.Address" --output text --region "$REGION")
ok "RDS endpoint: $RDS_ENDPOINT"

# Attach SG to RDS so the EC2 (also in SG) can reach Postgres 5432
RDS_SG=$(aws rds describe-db-instances --db-instance-identifier "$DB_INSTANCE_ID" --query "DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId" --output text --region "$REGION")
if [[ "$RDS_SG" != "$SG_ID" ]]; then
  log "Re-binding RDS to the FanPitch security group ..."
  aws rds modify-db-instance --db-instance-identifier "$DB_INSTANCE_ID" --vpc-security-group-ids "$SG_ID" --apply-immediately --region "$REGION" >/dev/null
fi
ok "RDS reachable from EC2."

# ─── 7. Billing alarms ───────────────────────────────────────────────
log "Setting up CloudWatch billing alarms (\$30 / \$40 / \$45) ..."
SNS_TOPIC_ARN=$(aws sns create-topic --name fanpitch-billing-alerts --region us-east-1 --query TopicArn --output text 2>/dev/null || echo "")
if [[ -n "$SNS_TOPIC_ARN" ]]; then
  for THRESHOLD in 30 40 45; do
    aws cloudwatch put-metric-alarm \
      --alarm-name "fanpitch-billing-$THRESHOLD-usd" \
      --alarm-description "FanPitch sandbox billing exceeds \$$THRESHOLD" \
      --metric-name EstimatedCharges \
      --namespace AWS/Billing \
      --statistic Maximum \
      --period 21600 \
      --evaluation-periods 1 \
      --threshold "$THRESHOLD" \
      --comparison-operator GreaterThanThreshold \
      --dimensions Name=Currency,Value=USD \
      --alarm-actions "$SNS_TOPIC_ARN" \
      --region us-east-1 2>/dev/null || warn "Alarm $THRESHOLD already exists or billing-metric not yet enabled."
  done
  ok "Billing alarms armed (subscribe to SNS topic: $SNS_TOPIC_ARN to get emails)."
else
  warn "Could not create SNS topic — skip billing alarms. Check 'Billing → Receive email alerts' in your AWS root settings."
fi

# ─── 8. Emit the next-step .env and SSH command ──────────────────────
log "Generating .env file for the EC2 host ..."
cat > "$ARTIFACTS_DIR/.env.prod" <<EOF
DJANGO_SECRET_KEY=$(python3 -c 'import secrets;print(secrets.token_urlsafe(64))')
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,$EC2_PUBLIC_DNS,$EC2_PUBLIC_IP

POSTGRES_DB=fanpitch
POSTGRES_USER=$DB_USER
POSTGRES_PASSWORD=$DB_PASSWORD
POSTGRES_HOST=$RDS_ENDPOINT
POSTGRES_PORT=5432

REDIS_URL=redis://redis:6379/0

CORS_ALLOWED_ORIGINS=http://$EC2_PUBLIC_DNS,http://$EC2_PUBLIC_DNS:8000,http://localhost:3000

AWS_REGION=$REGION
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

S3_BUCKET=$S3_BUCKET
CLOUDFRONT_DOMAIN=

BEDROCK_ENABLED=true
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0

FOOTBALL_DATA_API_KEY=
FOOTBALL_DATA_BASE_URL=https://api.football-data.org/v4

SIMULATOR_DEFAULT_SPEED=10
EOF
ok "Generated artifacts/.env.prod"

# Save a summary for human eyes
cat > "$ARTIFACTS_DIR/SUMMARY.txt" <<EOF
FanPitch — AWS Sandbox provisioning summary
============================================
Date: $(date)
Account: $ACCOUNT_ID
Region: $REGION

RDS Endpoint:      $RDS_ENDPOINT
RDS Username:      $DB_USER
RDS Password:      (see artifacts/db_password.txt)
S3 Bucket:         $S3_BUCKET
EC2 Instance:      $INSTANCE_ID
EC2 Public DNS:    $EC2_PUBLIC_DNS
EC2 Public IP:     $EC2_PUBLIC_IP
SSH Key:           artifacts/$KEY_NAME.pem
Security Group:    $SG_ID
IAM Role:          $ROLE_NAME

Next step — bootstrap the EC2:

  scp -i deploy/artifacts/$KEY_NAME.pem -o StrictHostKeyChecking=no \\
      deploy/artifacts/.env.prod ec2-user@$EC2_PUBLIC_DNS:/tmp/.env
  ssh -i deploy/artifacts/$KEY_NAME.pem -o StrictHostKeyChecking=no \\
      ec2-user@$EC2_PUBLIC_DNS 'bash -s' < deploy/setup_ec2_host.sh

Once that's done, the API is live at:

  http://$EC2_PUBLIC_DNS/api/docs/

And the Flutter app should be built with:

  flutter run --dart-define=API_BASE=http://$EC2_PUBLIC_DNS \\
              --dart-define=WS_BASE=ws://$EC2_PUBLIC_DNS
EOF
echo ""
echo -e "${C_GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_END}"
cat "$ARTIFACTS_DIR/SUMMARY.txt"
echo -e "${C_GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_END}"
ok "All AWS resources provisioned. Now run setup_ec2_host.sh on the EC2."
