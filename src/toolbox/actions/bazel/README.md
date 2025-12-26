# 🍃 Bazel Actions

High-performance, hermetic build and test tools for Bazel monorepos. This module handles authentication, version management, and environment isolation automatically.

## ✨ Features

* **Hybrid Authentication:** Supports both **SSH** (for Git dependencies) and **Netrc** (for HTTP/Artifactory dependencies).
* **Smart Versioning:** Automatically installs the correct Bazel version using `bazelisk`. Supports legacy (Workspace) and modern (Bzlmod) projects.
* **Automated Reporting:** Generates structured Markdown reports detailing successful, failed, and skipped targets via the Build Event Protocol (BEP).
* **SSH Directory Mounting:** Mount your entire local `.ssh` folder to support complex Git configurations (`config`, `known_hosts`).
* **Host Key Bypass:** Automatically disables `StrictHostKeyChecking` to prevent CI failures on unknown Git hosts.
* **Non-Root Execution:** Runs operations as a secure `developer` user.

---

## 🔐 Authentication Guide

Bazel often needs to clone private repositories. This module offers two ways to handle SSH:

### Option A: Mount Full SSH Directory (Recommended for Local/Dev)
Mounts your host's `~/.ssh` folder. This ensures Bazel uses your existing keys, SSH config aliases, and known hosts.

```bash
--ssh-dir "$HOME/.ssh"

```

### Option B: Inject Single Key (Recommended for CI)

Injects a specific private key as a Secret. Useful in CI pipelines (e.g., Jenkins, GitHub Actions) where you don't have a full `.ssh` folder.

```bash
--ssh-key file:$HOME/.ssh/id_rsa

```

### HTTP Auth (Netrc)

For private artifacts (Artifactory, Nexus), inject your `.netrc` file:

```bash
--netrc file:$HOME/.netrc

```

---

## 📋 Commands & Examples

### 1. `build`

Compiles the project targets and outputs the standard console log.

#### Basic Usage (Modern Bazel 7+)

```bash
dagger call build \
    --source . \
    --targets "//src/..."

```

#### Legacy Project (Bazel 6 or older)

Disables Bzlmod and forces a specific version.

```bash
dagger call build \
    --source . \
    --bazel-version "6.4.0" \
    --bzlmod=false \
    --targets "//..."

```

---

### 2. `build-with-report`

Executes the build and generates a **Markdown report** (`build_report.md`) summarizing the status of every target (Success, Failed, or Skipped). This is ideal for CI summaries or GitHub/GitLab PR comments.

#### Generate and Export Report

```bash
dagger call build-with-report \
    --source . \
    --targets "//..." \
    -o ./build_report.md

```

#### With Authentication

```bash
dagger call build-with-report \
    --source . \
    --ssh-dir "$HOME/.ssh" \
    --netrc file:$HOME/.netrc \
    -o ./artifacts/report.md

```

---

### 3. `test`

Runs tests and allows log configuration.

#### Run all tests (Hide logs on success)

Default behavior (`--test_output=errors`).

```bash
dagger call test --source .

```

#### Debugging Flaky Tests (Show all logs)

Forces output even if tests pass.

```bash
dagger call test \
    --source . \
    --test-output "all" \
    --targets "//src:unit_tests"

```

---

### 4. `query-to-file`

Exports dependency graphs or query results to a file. Essential for audits and migration analysis.

#### Export Dependency Graph

```bash
dagger call query-to-file \
    --source . \
    --query "deps(//...)" \
    -o ./dumps/full_graph.txt

```

#### Compare Legacy vs Modern Graph

Generate a graph forcing the legacy setup to compare with the new Bzlmod setup.

```bash
dagger call query-to-file \
    --source . \
    --bazel-version "6.4.0" \
    --bzlmod=false \
    --query "deps(//...)" \
    --ssh-dir "$HOME/.ssh" \
    -o ./dumps/legacy_deps.txt

```

---

## ⚙️ Arguments Reference

| Argument | Type | Description | Default |
| --- | --- | --- | --- |
| `--source` | `Directory` | Root directory of the repository (contains WORKSPACE/MODULE.bazel). | **Required** |
| `--targets` | `List[str]` | List of Bazel targets to build/test. | `["//..."]` |
| `--bazel-version` | `String` | Force a specific version (e.g., "7.1.1"). Overrides `.bazelversion`. | `None` (Latest) |
| `--bzlmod` | `Bool` | If `false` and version < 7, passes `--noenable_bzlmod`. | `true` |
| `--ssh-dir` | `Directory` | Mounts a full `.ssh` folder. | `None` |
| `--ssh-key` | `Secret` | Mounts a single private key to `~/.ssh/id_rsa`. | `None` |
| `--netrc` | `Secret` | Mounts credentials to `~/.netrc`. | `None` |
| `--test-output` | `String` | Bazel log level (`summary`, `errors`, `all`, `streamed`). | `"errors"` |

---

## 🐛 Troubleshooting

| Error | Cause | Solution |
| --- | --- | --- |
| `Permission denied (publickey)` | Git cannot authenticate. | Use `--ssh-dir "$HOME/.ssh"` or check if your `--ssh-key` is the **private** key (not `.pub`). |
| `noenable_bzlmod: Unrecognized option` | You are running a very old Bazel version that doesn't know this flag. | The module automatically handles this if you set `--bazel-version` correctly. Ensure you are not forcing flags manually. |
| `Artifactory 401 Unauthorized` | Netrc file missing or incorrect. | Verify your `.netrc` content and pass it via `--netrc file:$HOME/.netrc`. |
| `Report shows only "SKIPPED"` | Build failed early (e.g., dependency fetch) before targets could be attempted. | Check the console logs for network or `MODULE.bazel` resolution errors. |
