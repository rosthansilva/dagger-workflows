# 🧰 Dagger Platform Toolbox

A modular, enterprise-grade collection of Dagger functions designed to automate CI/CD workflows, infrastructure management, and developer experience.

## 🎯 Project Goals

* **Zero Local Dependencies:** Run complex tools like Bazel, Terraform, Zuul, and Git audits without installing them on your host.
* **Hermeticity:** Guaranteed "it works on my machine" through isolated, versioned containers.
* **Self-Documenting:** Rich CLI help and standardized READMEs for every module.
* **Automated Scaffolding:** Expand your toolbox consistently using built-in generator tools.

---

## 📚 Action Catalog

The toolbox is organized into specialized modules. Each has its own deep-dive documentation.

| Action | Description | Documentation |
| --- | --- | --- |
| **🏗️ Terraform** | Secure IaC with Plan/Apply immutability and auto-docs. | [View README](./src/toolbox/actions/terraform/README.md) |
| **🚦 Zuul CI** | Job scaffolding and playbook validation for Zuul environments. | [View README](./src/toolbox/actions/zuul/README.md) |
| **🐙 Git Utils** | Commit linting, auto-changelog, and repository health checks. | [View README](./src/toolbox/actions/git_utils/README.md) |
| **🍃 Bazel** | High-performance build tools with Workspace/Bzlmod hybrid support. | [View README](./src/toolbox/actions/bazel/README.md) |
| **🛠️ Dev** | **The Engine:** Automated scaffolding to create and register new actions. | [View README](./src/toolbox/actions/dev/README.md) |
| **🐍 Python** | Standardized linting and testing pipelines for Python projects. | [View README](./src/toolbox/actions/python_dev/README.md) |
| **💻 System** | Essential shell utilities and container environment inspection. | [View README](./src/toolbox/actions/system/README.md) |

---

## 🚀 Quick Start

### 1. Requirements

Ensure the [Dagger CLI](https://docs.dagger.io/install) is installed and your Docker engine is running.

### 2. Discover Functions

Explore the available modules directly from your terminal:

```bash
# List all top-level modules
dagger functions

# Explore a specific module (e.g., Git Utils)
dagger call git-utils --help

```

### 3. Scaling the Toolbox (Scaffolding)

To add a new tool (e.g., `kubernetes`) following all project standards:

```bash
dagger call dev new-action --name kubernetes --source src -o src

```

---

## 🔐 Security & Secrets

This toolbox utilizes Dagger's `Secret` type. Sensitive data (AWS ARNs, API Tokens, SSH Keys) is never stored in image layers or exposed in logs.

**Example: Passing a local SSH key for private git clones:**

```bash
dagger call bazel build --source . --ssh-key file:$HOME/.ssh/id_rsa

```

---

## 🛠️ Project Architecture

The project follows a **Router-Action** pattern. The `main.py` acts as a central dispatcher, while each directory in `actions/` contains isolated logic.

```text
.
├── src/
│   └── toolbox/
│       ├── main.py             # Global Router (#FROMLINES marker)
│       └── actions/            # Domain-Specific Actions
│           ├── <action_name>/
│           │   ├── main.py     # Dagger Logic (Python SDK)
│           │   └── README.md   # Action Documentation

```


dagger call bazel test     --source examples/bazel-tests-examples     --targets "//..."
dagger call bazel query-to-file     --source examples/bazel-tests-examples     --bzlmod=false     --bazel-version="7.1.1"     --query "deps(//...)"     -o ./dumps/graph_legacy.txt