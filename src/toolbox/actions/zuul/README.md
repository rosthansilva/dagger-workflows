# 🚦 Zuul CI Actions

This module provides high-level automation for **Zuul CI**, focusing on rapid job scaffolding, playbook generation, and multi-layer validation of configuration files.



## ✨ Key Features

- **Instant Scaffolding:** Generate a complete Zuul job definition along with its corresponding Ansible playbook structure in seconds.
- **Deep Validation:** Combines YAML schema validation with `ansible-lint` to ensure playbooks follow best practices before they reach the executor.
- **Enforced Standards:** Ensures all jobs follow organizational conventions for `nodesets`, `parents`, and directory layouts.
- **Dry-Run Friendly:** Perfect for local development to verify configurations without waiting for the Zuul Scheduler to report errors.

## 📋 Commands

### `generate-job`
Creates a standardized Zuul job YAML file and a boilerplate Ansible playbook.

```bash
# Example: Creating a new integration test job
dagger call zuul generate-job \
  --name "api-integration-test" \
  --parent "base-python-job" \
  --nodeset "ubuntu-jammy-large" \
  --source . \
  -o .

```

### `lint`

Performs a comprehensive check on all Zuul configurations and Ansible playbooks within the repository.

```bash
dagger call zuul lint --source .

```

---

## 🏗️ Expected Repository Structure

The module follows the standard Zuul configuration layout. Using `generate-job` will automatically maintain this structure:

```text
.
├── zuul.d/                # Contains Job, Project, and Pipeline definitions
│   └── jobs-<name>.yaml   # Individual job configurations
└── playbooks/             # Ansible playbooks referenced by the jobs
    └── <job-name>/
        └── run.yaml       # Main execution entry point

```

## 🛠️ Configuration Details

The linting process uses a specialized container containing:

* **Python 3.11**
* **PyYAML** (for strict syntax checking)
* **ansible-lint** (for playbook quality)
* **zuul-client** (for advanced CLI interactions)

## 🐛 Troubleshooting

| Issue | Solution |
| --- | --- |
| `YAML load error` | A syntax error was found in one of the files in `zuul.d/`. Run `lint` to locate the file and line. |
| `ansible-lint` failures | Your playbook uses deprecated modules or insecure practices. Follow the suggestions in the `lint` command output. |
| `Job not found by Zuul` | Ensure the generated file in `zuul.d/` is being included in your `zuul.yaml` or project configuration. |

---

## 🔗 Integration with Toolbox

This module can be combined with other actions. For example, you can use the **Dev** action to extend this module or the **System** action to inspect the generated YAML files.

```bash
# Inspecting the generated job
dagger call system echo --message "$(cat zuul.d/jobs-api-integration-test.yaml)"

```

