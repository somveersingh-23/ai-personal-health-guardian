# Git Workflow

The repository uses short-lived feature branches based on `develop`. Branch names describe a feature; they are not nested directories.

## Start or resume Member 2 work

For a new local clone:

```powershell
git clone https://github.com/somveersingh-23/ai-personal-health-guardian.git
cd ai-personal-health-guardian
git fetch origin --prune
git switch feature/m2-sensor-intelligence
```

To create the branch only when it does not already exist:

```powershell
git switch develop
git pull --ff-only origin develop
git switch -c feature/m2-sensor-intelligence
git push -u origin feature/m2-sensor-intelligence
```

Do not run the creation command again for an existing branch.

## Synchronize safely

Before a new unit of work:

```powershell
git status
git fetch origin --prune
git switch feature/m2-sensor-intelligence
git merge origin/develop
```

Resolve conflicts deliberately and run all affected tests. Do not rewrite a shared branch's published history without team agreement.

## Review and publish

```powershell
git status --short
git diff
git add path\to\intended-file another\intended-file
git diff --cached
git commit -m "Validate sensor ingestion provenance"
git push origin feature/m2-sensor-intelligence
```

Open a pull request with base `develop` and compare `feature/m2-sensor-intelligence`. Never push feature work directly to `main`. The pull request must pass CI and identify changes to shared files, schemas, migrations, claims, datasets, or member handoffs.

## Recommended GitHub protection

Repository administrators should protect `develop` and `main` with pull requests, required CI, resolved conversations, and blocked force pushes/deletions. Require at least one other member's review for shared contracts. These are repository settings, not code changes, so an administrator must enable them on GitHub.

## Common misconception

Cloning or switching branches shows other members' code because Git branches contain complete snapshots. A push transfers only commits that the remote does not already have; it does not duplicate every inherited file. Deleting inherited Member 1 code from Member 2's branch would instead create deletion commits and break integration.
