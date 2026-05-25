# Branch protection — settings to apply once

The branches `main`, `staging`, `dev` exist on the remote but the protection
rules need to be enabled by an admin (you) in the GitHub UI. Same settings
apply to both `fanpitch-api` and `fanpitch-app` repos.

## Why protect them

- **`main`** is what's live on AWS. A bad push there breaks production.
- **`staging`** is what's tested manually before a release.
- **`dev`** is the shared integration point — accidental force-pushes there
  rewrite history for everyone.

## Settings to apply (GitHub UI walk-through)

1. Go to **Settings → Branches → Add branch ruleset** (or "Add classic
   branch protection rule" if you prefer the classic UI).
2. **Branch name pattern**: `main` (repeat for `staging` and `dev`).
3. Tick the following options:

### Required on all three branches

- ✅ **Require a pull request before merging**
  - ✅ Require approvals → **1** approval (you, since solo)
  - ✅ Dismiss stale pull request approvals when new commits are pushed
  - ✅ Require review from Code Owners
- ✅ **Require status checks to pass before merging**
  - ✅ Require branches to be up to date before merging
  - Select these checks (they must have run at least once for GitHub to
    know about them — push the first PR and they'll appear):
    - `lint` (from `ci.yml`)
    - `test` (from `ci.yml`)
    - `build-image` (from `ci.yml`) — backend only
    - `flutter-analyze` (from `ci.yml`) — frontend only
    - `flutter-test` (from `ci.yml`) — frontend only
    - `build-android` (from `ci.yml`) — frontend only
    - `commitlint` (from `ci.yml`)
    - `analyze (python)` (from `codeql.yml`) — backend only
    - `trivy-image` (from `security.yml`) — backend only
- ✅ **Require conversation resolution before merging**
- ✅ **Require signed commits** (optional but nice — turn this on once
  you've set up GPG / SSH commit signing).
- ✅ **Require linear history**
- ❌ **Do not allow force pushes**
- ❌ **Do not allow deletions**

### Extra for `main` only

- ✅ **Restrict who can push to matching branches** → only admins
- ✅ **Lock branch** → off (we still need to push squash-merge commits
  through GitHub itself, just not direct pushes).

## Or apply via `gh` CLI

If you have the GitHub CLI configured with an admin token:

```bash
# For each repo, for each branch:
for REPO in fanpitch-api fanpitch-app; do
  for BR in main staging dev; do
    gh api -X PUT "repos/Jonlandu/$REPO/branches/$BR/protection" \
      -F required_status_checks[strict]=true \
      -F enforce_admins=false \
      -F required_pull_request_reviews[required_approving_review_count]=1 \
      -F required_pull_request_reviews[dismiss_stale_reviews]=true \
      -F required_pull_request_reviews[require_code_owner_reviews]=true \
      -F required_linear_history=true \
      -F allow_force_pushes=false \
      -F allow_deletions=false \
      -f restrictions= 2>&1 | head -3
  done
done
```

Note: status checks need to be discovered first — push a PR, let CI run,
then add the check names via the UI or another `gh api` call.

## After applying

Verify with:

```bash
gh api repos/Jonlandu/fanpitch-api/branches/main/protection | jq .
```

You should see your settings echoed back.

## Workflow once protected

To merge anything to `main`:

```bash
git checkout dev
git pull
git checkout -b feature/your-thing
# ... commit, commit, commit ...
git push -u origin feature/your-thing
gh pr create --base dev --fill
# After review + CI green:
gh pr merge --squash --delete-branch

# When dev is stable:
gh pr create --base staging --head dev --title "Release candidate vX.Y.Z"
# After staging QA passes:
gh pr create --base main --head staging --title "Promote vX.Y.Z to production"
# Merge the production PR → AWS deploy is triggered manually
git tag vX.Y.Z && git push --tags
```
