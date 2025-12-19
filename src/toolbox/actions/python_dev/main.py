import dagger
from dagger import object_type, function, Directory, dag # <--- Adicione 'dag'

@object_type
class PythonDev:
    """Pipeline padrão para projetos Python."""

    @function
    async def lint(self, source: Directory) -> str:
        # CORREÇÃO ABAIXO: Use 'dag.container()'
        return await (
            dag.container()
            .from_("python:3.11-slim")
            .with_exec(["pip", "install", "flake8"])
            .with_mounted_directory("/src", source)
            .with_workdir("/src")
            .with_exec(["flake8", "."])
            .stdout()
        )