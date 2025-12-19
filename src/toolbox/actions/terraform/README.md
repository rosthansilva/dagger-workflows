# 🏗️ Terraform Actions

This module provides a hermetic, containerized workflow for Terraform automation, replacing the need for local installations of `terraform`, `tfenv`, or `terraform-docs`.

## ✨ Features

- **Multi-Environment Support:** Native handling for `dev` and `prod` environments.
- **Secure Secret Injection:** Uses Dagger's `Secret` type for ARNs and API Tokens (never exposed in logs).
- **Immutable Workflows:** Enforces a Plan-then-Apply pattern by passing plan files between functions.
- **Automated Documentation:** Built-in `terraform-docs` integration.
- **Hermeticity:** Runs in an isolated Alpine-based environment with predictable tool versions.

## 📋 Commands

### `plan`
Initializes Terraform and generates a binary execution plan file.

```bash
dagger call terraform plan \
  --source . \
  --env dev \
  --dev-arn env:DEV_ARN \
  --cloudflare-token env:CF_TOKEN \
  -o ./tfplan.dev

```

### `apply`

Applies a previously generated execution plan file.

```bash
dagger call terraform apply \
  --source . \
  --env dev \
  --dev-arn env:DEV_ARN \
  --plan file:./tfplan.dev

```

### `docs`

Generates Markdown documentation for your HCL code using `terraform-docs`.

```bash
dagger call terraform docs \
  --source . \
  -o ./docs/README.md

```

### `state-rm`

Safely removes a specific resource address from the Terraform state.

```bash
dagger call terraform state-rm \
  --source . \
  --env prod \
  --prod-arn env:PROD_ARN \
  --address "aws_instance.web_server"

```

## 🔐 Environment & Secrets

The module requires specific secrets to be passed depending on the environment. You can load them from your local environment variables using the `env:` prefix.

| Argument | Description | Required For |
| --- | --- | --- |
| `--dev-arn` | AWS IAM Role ARN for Dev | `env == "dev"` |
| `--prod-arn` | AWS IAM Role ARN for Prod | `env == "prod"` |
| `--cloudflare-token` | Cloudflare API Token | Cloudflare resources |
| `--cloudflare-zone` | Cloudflare Zone ID | Cloudflare resources |

## 📐 Architecture

The workflow is designed to be **stateless**. The `plan` function outputs a physical file to your host, which you then feed into the `apply` function. This ensures that the exact changes reviewed in the plan are the ones applied to your infrastructure.

## 🐛 Troubleshooting

| Issue | Solution |
| --- | --- |
| `ARN for environment 'prod' must be provided` | You forgot to pass `--prod-arn env:PROD_ARN` while using `--env prod`. |
| `terraform-docs: command not found` | Ensure you are using the `base()` container provided by this module. |
| `Error: No such file or directory (tfplan.dev)` | Ensure you generated the plan first and provided the correct path to the `--plan` argument. |


