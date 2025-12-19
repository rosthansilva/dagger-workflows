# 🧰 Dagger Platform Toolbox

A modular, enterprise-grade collection of Dagger functions designed to automate CI/CD workflows, infrastructure management, and developer experience.

## 🎯 Project Goals

* **Zero Local Dependencies:** Run complex tools like Bazel, Terraform, and Zuul without installing them on your host.
* **Hermeticity:** Guaranteed "it works on my machine" through isolated, versioned containers.
* **Self-Documenting:** Rich CLI help and standardized READMEs for every module.
* **Automated Scaffolding:** Expand your toolbox consistently using built-in generator tools.

---

## 📚 Action Catalog

The toolbox is organized into specialized modules. Each has its own deep-dive documentation.

| Action | Description | Documentation |
| --- | --- | --- |
| **🏗️ Terraform** | Secure IaC with Plan/Apply immutability and auto-docs. | [View README](https://www.google.com/search?q=./src/toolbox/actions/terraform/README.md) |
| **🚦 Zuul CI** | Job scaffolding and playbook validation for Zuul environments. | [View README](https://www.google.com/search?q=./src/toolbox/actions/zuul/README.md) |
| **🍃 Bazel** | High-performance build tools with Workspace/Bzlmod hybrid support. | [View README](https://www.google.com/search?q=./src/toolbox/actions/bazel/README.md) |
| **🛠️ Dev** | **The Engine:** Automated scaffolding to create and register new actions. | [View README](https://www.google.com/search?q=./src/toolbox/actions/dev/README.md) |
| **🐍 Python** | Standardized linting and testing pipelines for Python projects. | [View README](https://www.google.com/search?q=./src/toolbox/actions/python_dev/README.md) |
| **💻 System** | Essential shell utilities and container environment inspection. | [View README](https://www.google.com/search?q=./src/toolbox/actions/system/README.md) |

---

## 🚀 Quick Start

### 1. Requirements

Ensure the [Dagger CLI](https://docs.dagger.io/install) is installed and your Docker engine is running.

### 2. Discover Functions

Explore the available modules directly from your terminal:

```bash
# List all top-level modules
dagger functions

# Explore a specific module (e.g., Zuul)
dagger call zuul --help

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
│           │   ├── main.py     # Dagger Logic
│           │   └── README.md   # Action Documentation

```
