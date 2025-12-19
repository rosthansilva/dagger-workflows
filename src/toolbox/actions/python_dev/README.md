# 🐍 Python Developer Tools

Standardized pipelines for Python development to ensure code quality across all projects.

## 📋 Commands

### `lint`
Runs `flake8` on the source code to check for style violations.

```bash
dagger call python lint --source .

```

## ⚙️ Configuration

The tools run inside a `python:3.11-slim` container. Ensure your project has a compatible `pyproject.toml` or configuration file if you need custom linting rules.
