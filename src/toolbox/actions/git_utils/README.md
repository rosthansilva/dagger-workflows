# 🐙 Git Utilities

Save time on daily Git maintenance and ensure CI compliance with automated audits.



## ✨ Features

- **Commit Linting:** Enforce Conventional Commits patterns.
- **Auto-Changelog:** Quickly see what changed since the last release.
- **Repository Health:** Identify stale merged branches that clutter your workspace.
- **SemVer Intelligence:** Suggest the next version based on commit history.

## 📋 Commands

### `commit-lint`
Validates the last N commits for standards.
```bash
dagger call git-utils commit-lint --source . --commits-count 10

```

### `detect-merged-branches`

Finds branches that are already merged and can be deleted.

```bash
dagger call git-utils detect-merged-branches --source . --main-branch "main"

```

### `suggest-next-version`

Scans recent commits for "feat", "fix", or "BREAKING CHANGE" to suggest a version bump.

```bash
dagger call git-utils suggest-next-version --source .

```
