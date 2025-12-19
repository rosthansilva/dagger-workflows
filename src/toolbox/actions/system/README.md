# 💻 System Utilities

General purpose helper functions for shell interaction and debugging within the Dagger engine.

## 📋 Commands

### `info`
Returns information about the execution environment (OS, Arch).

```bash
dagger call system info

```

### `echo`

Simple echo command for pipeline testing.

```bash
dagger call system echo --message "Hello World"

```

```

### 💡 Pro Tip: Keeping Docs Updated

Since we used `Annotated` and `Doc` in the Python code, the CLI help is always accurate. You can verify this by running:

```bash
dagger call bazel --help

```