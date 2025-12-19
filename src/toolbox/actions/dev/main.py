import dagger
from dagger import object_type, function, Directory, dag, Doc
from typing import Annotated

@object_type
class Dev:
    """
    Toolbox development utilities.
    Helps scaffold new actions and maintain the project structure.
    """

    @function
    def new_action(
        self,
        name: Annotated[str, Doc("The name of the new action (snake_case), e.g., 'k8s_utils'")],
        source: Annotated[Directory, Doc("The 'src' directory of your toolbox")]
    ) -> Directory:
        """
        Scaffolds a new action with standard boilerplate code and documentation.
        
        This generates the folder structure, __init__.py, main.py, and README.md.
        
        Example:
            dagger call dev new-action --name "kafka" --source src -o src
        """
        
        # 1. Calculate names
        class_name = "".join(word.title() for word in name.split('_')) # snake_case to PascalCase
        base_path = f"toolbox/actions/{name}"

        # 2. Template for main.py
        main_py_content = f"""import dagger
from dagger import object_type, function, Directory, Container, dag, Doc
from typing import Annotated

@object_type
class {class_name}:
    \"\"\"
    Description for the {class_name} action.
    \"\"\"

    @function
    def info(self) -> str:
        \"\"\"Returns basic info about this module.\"\"\"
        return "Action {name} is ready!"
"""

        # 3. Template for README.md
        readme_content = f"""# 📦 {class_name} Actions

                 Description of what this module does.
                 
                 ## 📋 Commands
                 
                 ### `info`
                 Basic check command.
                 
                 ```bash
                 dagger call {name} info
                 """
        
        # 4. Generate the files inside the source directory structure
    # We start with a generic directory to ensure we are adding to the structure
        return (
        source
        .with_new_file(f"{base_path}/__init__.py", "")
        .with_new_file(f"{base_path}/main.py", main_py_content)
        .with_new_file(f"{base_path}/README.md", readme_content)
    )

### 3. Register `Dev` in `src/toolbox/main.py`

You need to manually register this new tool once.

```python
# ... existing imports
from .actions.bazel.main import Bazel
from .actions.dev.main import Dev  # <--- Add Import

@object_type
class Toolbox:
    # ... existing functions ...

    @function
    def dev(self) -> Dev:
        """Tools for maintaining and extending this Dagger Toolbox."""
        return Dev()