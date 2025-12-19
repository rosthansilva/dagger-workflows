# 🛠️ Dev Actions (Scaffolding)

The `dev` module is the meta-tool of this project. It automates the creation of new actions, ensuring they follow the project's architectural standards, directory structure, and registration requirements.



## ✨ Features

- **Automated Scaffolding:** Generates the folder, `__init__.py`, `main.py` (boilerplate), and `README.md` in one command.
- **Smart Registration:** Automatically injects the required `import` statement into `toolbox/main.py` using the `#FROMLINES` marker.
- **Route Injection:** Automatically appends the new module's access function to the `Toolbox` class.
- **Consistency:** Ensures every new tool starts with the same high-quality template and documentation structure.

## 📋 Commands

### `new-action`
Generates a new action skeleton and registers it globally in the toolbox.

```bash
# Syntax
dagger call dev new-action --name <action_name> --source src -o src

# Example: Creating a 'kubernetes' tool
dagger call dev new-action --name kubernetes --source src -o src

```

## 🏗️ How it Works

The scaffolding process follows a specific lifecycle to maintain project integrity:

1. **Naming:** Converts your `snake_case` input (e.g., `cloud_auth`) into `PascalCase` for the Python class (e.g., `CloudAuth`).
2. **Template Generation:** Creates a `main.py` with the Dagger `@object_type` and a sample `info` function.
3. **Internal Registration:** - It looks for the `#FROMLINES` comment in `src/toolbox/main.py`.
* It inserts the new import right below it.
* It appends the route method at the end of the `Toolbox` class.


4. **Filesystem Merge:** Using the `-o src` flag, it writes the new files and the modified `main.py` back to your host machine.

## 🛠️ Requirements for Automation

For the automatic registration to work, your `src/toolbox/main.py` **must** contain the `#FROMLINES` marker:

```python
# src/toolbox/main.py
import dagger
from dagger import object_type, function

#FROMLINES
from .actions.system.main import System
# ... new imports will appear here

```

## 🐛 Troubleshooting

| Issue | Solution |
| --- | --- |
| `Marker '#FROMLINES' not found` | Ensure you have the exact comment `#FROMLINES` in your `src/toolbox/main.py` file. |
| `ModuleNotFoundError` after creation | Ensure you ran the command with `-o src` to save the changes to your disk, then wait a second for Dagger to reload the module. |
| `Permission denied` | Ensure the `src` directory is writable by the user running the Dagger CLI. |

