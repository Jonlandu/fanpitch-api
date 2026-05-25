# FanPitch — AWS Innovation Sandbox deployment

End-to-end guide to ship the FanPitch backend on the Slalom hackathon **Innovation Sandbox** in **eu-central-1 (Frankfurt)**.

> **Why eu-central-1?** The DFL Bundesliga dataset lives there (`s3://aws-world-sports-innovation-cup-data/Challenge 3 – A Real Time Social Match Experience/`). Staying in-region avoids cross-region transfer cost.

> **Total wall-clock**: ~12 minutes (script does everything; RDS create is the slow step).
> **Total budget consumed**: ~$0.50 per day if the stack runs 24/7. With the $50 sandbox lease that's ~3 months of runway — plenty for the demo.

---

## Architecture

```
   📱 Flutter app  ──HTTP──▶  EC2 t2.micro (Docker compose: web + redis + worker + beat)
                  ──WS  ──▶   │
                              ├──▶ RDS PostgreSQL db.t4g.micro (private, SG-only)
                              ├──▶ S3 fanpitch-media-<accountId> (presigned PUTs)
                              └──▶ Bedrock Claude 3 Haiku (eu-central-1)
```

| Service | Sizing | Why |
|---|---|---|
| EC2 | `t2.micro` | Free Tier eligible; Docker hosts Daphne+Redis+Celery in one box |
| RDS | `db.t4g.micro`, 20 GB gp3 | Free Tier eligible; single-AZ; public-accessible (locked by SG) |
| S3 | `fanpitch-media-<acct>` | Lifecycle: uploads/ → IA after 7d, expire 30d |
| Bedrock | Claude 3 Haiku | ~$0.0003/req → 16k req fits $5 budget |
| Redis | In-container | ElastiCache not confirmed in sandbox; on-EC2 is free |

---

## Pre-flight checklist

- [ ] You have an active **lease** on the sandbox dashboard (`https://slalom-hackathon.awsapps.com/start` → Applications → Innovation Sandbox → Request lease).
- [ ] AWS CLI v2 installed locally (`brew install awscli` if not).
- [ ] You have requested **Bedrock model access** for `Anthropic — Claude 3 Haiku` in **eu-central-1** (Bedrock console → Model access → Modify model access).
- [ ] You have a GitHub repo for `fanpitch-api` (private OK; the EC2 will `git clone` from it).
- [ ] You have ~15 min of uninterrupted time (the script is mostly hands-off but you'll need to act if RDS rejects something).

---

## Step 1 — Configure AWS CLI with the sandbox credentials

From the sandbox dashboard, click **Login to account** → **Access keys** next to `myisb_IsbUsersPS`. You'll see something like:

```ini
[fanpitch-sandbox]
aws_access_key_id = ASIA...
aws_secret_access_key = ...
aws_session_token = ...
```

Append that block to `~/.aws/credentials` (create the file if missing).

Verify:
```bash
AWS_PROFILE=fanpitch-sandbox aws sts get-caller-identity
# → Account, UserId, Arn
```

> **Heads-up**: these credentials **expire every ~4 hours**. When that happens, just grab fresh ones from the sandbox dashboard and overwrite the block.

---

## Step 2 — Provision AWS resources

```bash
cd fanpitch-api
AWS_PROFILE=fanpitch-sandbox bash deploy/setup_aws_sandbox.sh
```

What this does (~10 min):
1. Creates the S3 bucket with CORS + lifecycle + public-access-block.
2. Kicks off RDS creation (the slow step — runs in background).
3. Creates EC2 key pair → saves `.pem` to `deploy/artifacts/`.
4. Creates security group with ingress on 22/80/443/8000 and Postgres-within-SG.
5. Creates IAM role with S3 + Bedrock + CloudWatch permissions and an instance profile.
6. Launches the EC2 t2.micro.
7. Waits for RDS to be ready, re-binds it to the security group.
8. Sets up CloudWatch billing alarms at $30/$40/$45.
9. Generates `deploy/artifacts/.env.prod` ready to ship to the EC2.

The script ends by printing a `SUMMARY.txt` with every value you need.

---

## Step 3 — Bootstrap the EC2 host

Copy `.env` to the EC2 and run the host setup script:

```bash
# Substitute values from artifacts/SUMMARY.txt
EC2_DNS="ec2-xx-xx-xx-xx.eu-central-1.compute.amazonaws.com"
KEY="deploy/artifacts/fanpitch-sandbox-key.pem"

# 1. Push the .env to /tmp/.env on the EC2
scp -i $KEY -o StrictHostKeyChecking=no \
    deploy/artifacts/.env.prod ec2-user@$EC2_DNS:/tmp/.env

# 2. Run the bootstrap script remotely
#    Edit deploy/setup_ec2_host.sh first to point REPO_URL at YOUR GitHub repo.
ssh -i $KEY -o StrictHostKeyChecking=no \
    ec2-user@$EC2_DNS 'bash -s' < deploy/setup_ec2_host.sh
```

The script installs Docker + Compose, clones the repo, builds the image, runs migrations, seeds demo data, and prints the live API URL.

---

## Step 4 — Verify

```bash
curl -s http://$EC2_DNS/api/docs/ | head -3
# → Should be HTML.
```

Open `http://$EC2_DNS/api/docs/` in a browser. You should see the OpenAPI Swagger UI.

Then point the Flutter app at the live backend:
```bash
cd ../fanpitch-app
flutter run -d "iPhone 15" \
  --dart-define=API_BASE=http://$EC2_DNS \
  --dart-define=WS_BASE=ws://$EC2_DNS
```

Login with `admin / admin12345` (seeded by `demo_setup`).

---

## Step 5 — Run the live demo

Open a second SSH session and run the simulator + bots:

```bash
ssh -i $KEY ec2-user@$EC2_DNS \
  'sudo docker compose -f fanpitch-api/docker-compose.prod.yml exec -T web \
     python manage.py run_demo --speed 10'
```

You'll see ~90 events broadcast in 9 seconds, with 7 bot personas reacting/commenting/posting. The mobile app updates in real time over WebSocket.

---

## Daily ops

### Watch logs
```bash
ssh -i $KEY ec2-user@$EC2_DNS \
  'sudo docker compose -f fanpitch-api/docker-compose.prod.yml logs -f web'
```

### Stop the stack to save budget (preserves DB)
```bash
ssh -i $KEY ec2-user@$EC2_DNS \
  'sudo docker compose -f fanpitch-api/docker-compose.prod.yml stop'
```

### Stop the EC2 entirely (RDS still bills)
```bash
aws ec2 stop-instances --instance-ids <i-...> --region eu-central-1
```

### Restart after stopping
```bash
aws ec2 start-instances --instance-ids <i-...> --region eu-central-1
# Note: the public DNS may change. Refresh artifacts/SUMMARY.txt.
```

### Check budget consumed
- Sandbox dashboard → My Leases → Budget bar.
- AWS console → Billing → Cost Explorer (filtered on `project=fanpitch` tag).

---

## Tear-down (before lease expiry)

```bash
AWS_PROFILE=fanpitch-sandbox bash deploy/teardown_aws_sandbox.sh
# type 'destroy' to confirm.
```

This deletes the EC2, RDS, S3 bucket contents, security group, IAM role, and key pair — leaving the sandbox clean.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `An error occurred (UnauthorizedOperation)` | Sandbox token expired. Refresh creds from the dashboard. |
| `aws s3api create-bucket … BucketAlreadyExists` | Bucket name is global. Change `S3_BUCKET` in the script. |
| RDS stays `creating` for >10 min | Sandbox sometimes throttles — wait, or check console for failure reason. |
| `docker: command not found` on EC2 | The first SSH may not have the docker group yet — run `sudo` or re-SSH. |
| Flutter app gets `Connection refused` | EC2 security group blocked port 80 — re-run `authorize-security-group-ingress` for port 80. |
| WebSocket disconnects with 4401 | JWT expired (30-min TTL). Sign out / sign in in the app. |
| Bedrock returns `AccessDeniedException` | Model access not yet granted. Bedrock console → Model access → Anthropic. |

---

## Cost guardrails (don't blow the $50 budget)

- ✅ **Stop the EC2** when not actively demoing (`aws ec2 stop-instances`).
- ✅ **Disable Bedrock** in `.env` (`BEDROCK_ENABLED=false`) for everyday dev — only flip on for the demo recording.
- ✅ **Lifecycle on S3 uploads/** — already configured (IA after 7d, expire 30d).
- ✅ **CloudWatch log retention 7 days** — set in `setup_aws_sandbox.sh`.
- ✅ **Billing alarms at $30/$40/$45** — armed automatically; email subscribers via the SNS topic in artifacts/SUMMARY.txt.
- ⚠️ **Watch for**: RDS storage growth (free under 20 GB), S3 GET requests (cheap but not zero), Bedrock per-token cost.
