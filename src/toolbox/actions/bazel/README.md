# 🍃 Bazel Actions

A comprehensive set of functions to handle complex Bazel builds, focusing on hermetic environments, remote caching, and migration scenarios.

## ✨ Features

* **Auto-Versioning:** Uses `bazelisk` to respect `.bazelversion` or allows overrides via arguments.
* **Safe Migration:** Intelligent flags to handle legacy projects (Workspace) vs. modern ones (Bzlmod).
* **Authentication:** Secure support for private Git repos (SSH) and Artifact registries (Netrc).
* **Multi-Architecture:** Automatically detects if running on AMD64 or ARM64.

## 📋 Available Commands

### `build`
Builds specific targets.

```bash
# Standard build (uses .bazelversion)
dagger call bazel build --source .

# Force legacy version (e.g., for regression testing)
dagger call bazel build --source . --bazel-version "6.4.0" --bzlmod=false

```

### `test`

Runs tests with controllable log verbosity.

```bash
# View full logs even if tests pass (useful for debugging flaky tests)
dagger call bazel test --source . --test-output "all"

```

### `query-to-file` (Auditing)

Exports the dependency graph to a local file. Essential for comparing changes during migrations (e.g., Workspace to Bzlmod).

```bash
dagger call bazel query-to-file \
    --source . \
    --query "deps(//...)" \
    -o ./dumps/current_graph.txt

```

## 🔐 Authentication (SSH & Netrc)

For projects depending on private repositories, you must inject local credentials. **No credentials are saved in the final image.**

### Using SSH Keys (Git)

Required for private Git dependencies.

```bash
dagger call bazel build \
    --source . \
    --ssh-key file:$HOME/.ssh/id_rsa

```

### Using Netrc (Artifactory/Nexus)

Required for private HTTP artifacts.

```bash
dagger call bazel build \
    --source . \
    --netrc file:$HOME/.netrc

```

## 🐛 Common Troubleshooting

| Error | Solution |
| --- | --- |
| `unexpected keyword argument 'managed_directories'` | You are running a Bazel 6 project using Bazel 7. Use `--bazel-version="6.4.0"`. |
| `Authentication failed for git@github.com` | You forgot to pass `--ssh-key file:$HOME/.ssh/id_rsa`. |
| `javac not found` | The project is not hermetic. Ensure your toolchain rules download the JDK. |
