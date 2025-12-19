import dagger
from dagger import object_type, function, Directory, Container, dag, Doc
from typing import Annotated, Optional

@object_type
class Zuul:
    """
    Automate Zuul CI job creation and configuration validation.
    """

    @function
    def base(self) -> Container:
        """
        Base container with zuul-client and ansible-lint.
        """
        return (
            dag.container()
            .from_("python:3.11-slim")
            .with_exec(["pip", "install", "zuul-client", "ansible-lint", "pyyaml"])
        )

    @function
    @function
    def generate_job(
        self,
        # O 'source' deve vir primeiro porque não tem valor padrão (=)
        source: Annotated[Directory, Doc("Target directory to save the yaml")],
        name: Annotated[str, Doc("Name of the Zuul job")],
        parent: Annotated[str, Doc("Parent job (e.g., base, python-test)")] = "base",
        nodeset: Annotated[str, Doc("Nodeset name")] = "ubuntu-jammy",
    ) -> Directory:
        """
        Generates a standard Zuul job definition YAML.
        
        Example:
            dagger call zuul generate-job --name "my-new-job" --source . -o .
        """
        job_yaml = f"""- job:
    name: {name}
    parent: {parent}
    nodeset: {nodeset}
    description: |
      Automatically generated job for {name}.
    run: playbooks/{name}/run.yaml
"""
        # Create the job file and the playbook directory/file
        playbook_boilerplate = f"""- hosts: all
  tasks:
    - name: Generated task for {name}
      debug:
        msg: "Hello from Zuul job {name}"
"""

        return (
            source
            .with_new_file(f"zuul.d/jobs-{name}.yaml", job_yaml)
            .with_new_file(f"playbooks/{name}/run.yaml", playbook_boilerplate)
        )

    @function
    async def lint(
        self,
        source: Annotated[Directory, Doc("The directory containing zuul.d/")]
    ) -> str:
        """
        Validates Zuul YAML syntax and Ansible playbooks.
        """
        return await (
            self.base()
            .with_mounted_directory("/src", source)
            .with_workdir("/src")
            # We use python to validate YAML syntax first
            .with_exec(["python3", "-c", "import yaml, glob; [yaml.safe_load(open(f)) for f in glob.glob('zuul.d/*.yaml')]"])
            .with_exec(["ansible-lint", "playbooks/"])
            .stdout()
        )