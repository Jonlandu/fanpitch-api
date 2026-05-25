# Solo DevOps playbook

> The cheat sheet for managing FanPitch as a one-person team with proper
> hygiene. Branches, releases, deployments, demos — all the recipes.

---

## TL;DR — the 4 commands you'll use 95% of the time

```bash
# 1. Start a new piece of work
git checkout dev && git pull
git checkout -b feature/clickable-profile

# 2. Promote dev → staging → main (via PRs, never direct push)
gh pr create --base dev    --head feature/clickable-profile --fill
gh pr create --base staging --head dev
gh pr create --base main    --head staging

# 3. Deploy to AWS
bash deploy/deploy.sh

# 4. Run the live demo (with crowd bots)
ssh -i deploy/artifacts/fanpitch-sandbox-key.pem ec2-user@<EC2_DNS> \
  'sudo docker compose -f /home/ec2-user/fanpitch-api/docker-compose.prod.yml exec -T web python manage.py run_demo --speed 10'
```

---

## Mental model — branches vs environments

| Branches (code quality gates)               | Environments (where it runs)             |
|----------------------------------------------|------------------------------------------|
| `feature/*` — work-in-progress              | `local` — your laptop docker compose     |
| `dev` — features integrated                 | `prod` — the AWS EC2 sandbox             |
| `staging` — pre-release smoke tested        |                                          |
| `main` — production-ready                   |                                          |

You only get **one EC2** in the AWS sandbox ($50 budget). So `dev` and
`staging` branches don't have their own deployed backend — they live in
code only, and you smoke-test them locally.

When `main` moves, you **deploy to the one EC2**. That's "production".

---

## Daily workflow — recipes

### Start a new feature

```bash
git checkout dev
git pull
git checkout -b feature/<short-name>

# ... code, commit, commit ...
# Commits MUST follow Conventional Commits (enforced by CI):
#   feat(scope): summary
#   fix(scope):  summary

git push -u origin feature/<short-name>
gh pr create --base dev --fill        # opens the PR, fills from template
```

### Iterate on the open PR

Just `git commit` + `git push` on the same branch. CI re-runs on each push.
When CI is green and you've self-reviewed:

```bash
gh pr merge --squash --delete-branch   # squashes into a single commit on dev
```

### Promote `dev` → `staging` (a "release candidate")

```bash
gh pr create --base staging --head dev --title "Release candidate $(date +%Y.%m.%d)"
# Run the tests locally one more time:
docker compose up -d
python manage.py test       # backend
cd ../fanpitch-app && flutter test    # frontend
# When happy:
gh pr merge --squash
```

### Promote `staging` → `main` and DEPLOY

```bash
gh pr create --base main --head staging --title "Promote $(git rev-parse --short HEAD) to prod"
# CI runs all checks again. When green:
gh pr merge --squash

# Tag the release (semver-ish):
git tag v0.2.0 && git push --tags

# Deploy to AWS:
git checkout main && git pull
bash deploy/deploy.sh
```

### Hot-fix a bug already on `main`

```bash
git checkout main && git pull
git checkout -b fix/critical-bug
# ... fix, commit ...
git push -u origin fix/critical-bug
gh pr create --base main --head fix/critical-bug --label hotfix
# After merge:
bash deploy/deploy.sh

# Don't forget to back-port to staging + dev so they don't drift:
git checkout staging && git merge main && git push
git checkout dev     && git merge main && git push
```

---

## Local demos (zero AWS needed)

The full stack runs in Docker on your laptop. Useful for the 3-min
demo video if you can't depend on the sandbox EC2 being up.

```bash
# Backend
cd fanpitch-api
docker compose up -d
docker compose exec web python manage.py demo_setup
docker compose exec web python manage.py run_demo --speed 10  # in a 2nd terminal

# Frontend
cd ../fanpitch-app
bash scripts/run.sh local                   # iOS sim + localhost backend
# or
bash scripts/run.sh lan "iPhone 15"         # iPhone on Wi-Fi + your LAN IP backend
```

The env badge in the top-right corner shows `LOCAL` so you (and any
tester) know which backend you're hitting.

---

## Build & ship the APK

```bash
cd fanpitch-app

# Build an APK that hits the live AWS backend (what testers want):
bash scripts/build.sh apk prod

# Build an APK that hits localhost (only useful on Android emulator):
bash scripts/build.sh apk local

# Output goes to dist/<env>/fanpitch-<version>-<env>-<timestamp>.apk
# Share that file directly (Google Drive / Dropbox / WhatsApp).
```

The APK is signed in **debug mode** by default — testers need to
toggle "Install unknown apps" once. For a Play Store build:

```bash
bash scripts/build.sh appbundle prod     # produces an .aab
```

iOS:
```bash
bash scripts/build.sh ipa prod            # needs Xcode signing config
```

---

## Testers can use the live backend ✅

The AWS EC2 is **publicly reachable** on port 80 (no auth needed to
hit the API — Django enforces auth per endpoint). Anyone you give an
APK to, anywhere in the world, can talk to:

```
http://ec2-63-184-221-33.eu-central-1.compute.amazonaws.com
```

⚠️ **Important caveats**:

- The sandbox EC2 IP **rotates every 4h** when the lease refreshes.
  Each new lease = new public DNS = need to rebuild the APK with the
  new URL.  Workflow: refresh creds → check `deploy/artifacts/SUMMARY.txt`
  for the new DNS → rebuild APK → reshare.
- **HTTP, not HTTPS** — fine for the hackathon demo, not for a public
  release. Production would need a real domain + Let's Encrypt cert.
- Demo credentials are seeded and printed by `demo_setup`. Tell your
  testers to use `admin / admin12345` or `kinshasa_kid / fanpitch1234`.

---

## When the sandbox lease expires

The 4h credential TTL is the trickiest part of the sandbox. Routine:

```bash
# 1. Go to the sandbox dashboard, click "Access keys", copy the block.
# 2. Open ~/.aws/credentials and replace the [709184586211_slalom_IsbUsersPS] block.
# 3. Verify:
AWS_PROFILE=709184586211_slalom_IsbUsersPS aws sts get-caller-identity

# 4. The EC2 keeps running — the credential refresh is for YOUR commands,
#    not for the running container. So as long as the EC2 is alive, the
#    backend keeps serving traffic. Only re-deploy / new-resource commands
#    need fresh creds.

# 5. If the EC2 was wiped (lease expired entirely → wipe-out), re-run:
AWS_PROFILE=709184586211_slalom_IsbUsersPS bash deploy/setup_aws_sandbox.sh
bash deploy/deploy.sh
```

---

## Cost guardrails

- **Stop the EC2** when you're not demoing or testing:
  ```bash
  AWS_PROFILE=709184586211_slalom_IsbUsersPS \
    aws ec2 stop-instances --instance-ids $(grep "EC2 Instance" deploy/artifacts/SUMMARY.txt | awk '{print $3}')
  ```
  Saves ~$0.30/day. Restart with `aws ec2 start-instances` — note the
  public DNS may change.
- **Disable Bedrock** (`BEDROCK_ENABLED=false` in `.env`) outside of
  demos. Each Bedrock call is ~$0.0003 → bursts add up.
- **Watch the lease budget bar** in the sandbox dashboard. At 60% I'd
  pause for a day.

---

## CI-driven deploy (future, not yet wired)

When you want to fully automate, the path is:

1. Add `.github/workflows/deploy.yml` triggered on `workflow_dispatch`
   (manual button in GitHub UI) and on `push: tags: ["v*"]`.
2. Use `aws-actions/configure-aws-credentials@v4` with **OIDC** + an
   IAM role you trust GitHub to assume (avoids long-lived AWS keys).
3. The workflow does what `deploy.sh` does today: rsync over SSH + run
   the remote bootstrap.

In the sandbox the OIDC config is fragile (4h TTL on the assumed-role
session), so for the hackathon, keep using `deploy.sh` from your
laptop. Document the future plan in `ARCHITECTURE.md` — judges value
the *intentional* simplification.
