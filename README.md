# 🧰 My Dagger Toolbox

This repository contains a centralized collection of Dagger functions for CI/CD automation, environment standardization, and local development tasks.

## 🚀 How to Use

Ensure you have the [Dagger CLI](https://docs.dagger.io/install) installed.

```bash
# List all available functions
dagger functions

# Get help for a specific module
dagger call bazel --help

```

## 📚 Module Catalog

| Module | Description | Link |
| --- | --- | --- |
| **Bazel** | Build, Test, and Queries for monorepos (Hybrid Workspace/Bzlmod support). | [View Docs](./src/toolbox/actions/bazel/README.md) |
| **Python** | Linting, formatting, and testing for Python projects. | [View Docs](./src/toolbox/actions/python_dev/README.md) |
| **System** | Shell utilities and container inspection tools. | [View Docs](./src/toolbox/actions/system/README.md) |

## 🛠️ Development

To add a new action:

1. Create a folder at `src/toolbox/actions/<name>`.
2. Implement the class using `@object_type`.
3. Register it in `src/toolbox/main.py`.
4. Create a `README.md` in the folder following the standard format.


