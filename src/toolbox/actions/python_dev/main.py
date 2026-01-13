import dagger
from dagger import object_type, function, Directory, Container, dag
from typing import Annotated

@object_type
class PythonDev:
    """
    Motor de desenvolvimento Python totalmente acelerado pelo 'uv'.
    Usa caminhos absolutos e Virtual Environments para build robusto.
    """

    @function
    def base(self, source: Directory) -> Container:
        """
        Ambiente de desenvolvimento base.
        """
        uv_bin = dag.container().from_("ghcr.io/astral-sh/uv:latest").file("/uv")

        return (
            dag.container()
            .from_("python:3.12-slim")
            .with_file("/bin/uv", uv_bin)
            .with_directory("/app", source)
            .with_workdir("/app")
            .with_exec(["apt-get", "update"])
            .with_exec(["apt-get", "install", "-y", "git"])
            # Setup VENV Dev
            .with_exec(["/bin/uv", "venv", "/app/.venv"])
            .with_exec(["/bin/uv", "pip", "install", ".[dev,test]"])
            # Configura PATH Dev
            .with_env_variable("VIRTUAL_ENV", "/app/.venv")
            .with_env_variable(
                "PATH", 
                "/app/.venv/bin:/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin"
            )
            .with_env_variable("PYTHONUNBUFFERED", "1")
        )

    @function
    async def check_quality(
        self, 
        source: Directory, 
        ignore_errors: bool = False
    ) -> str:
        """
        Roda Lint e Testes.
        """
        ctr = self.base(source)

        lint_commands = [
            ["uv", "run", "black", "--check", "."],
            ["uv", "run", "ruff", "check", "."],
            ["uv", "run", "bandit", "-r", "src"]
        ]

        print(f"🔍 Rodando Lint (Ignorar erros: {ignore_errors})...")

        for cmd in lint_commands:
            tool_name = cmd[2]
            try:
                await ctr.with_exec(cmd).sync()
                print(f"✅ {tool_name} passou.")
            except Exception as e:
                if ignore_errors:
                    print(f"⚠️  ALERTA: {tool_name} falhou, mas ignorando...")
                else:
                    print(f"❌ {tool_name} falhou. Abortando.")
                    raise e

        print("🧪 Rodando Testes Unitários...")
        tests = ctr.with_exec(["uv", "run", "pytest"])
        await tests.sync()
        
        return "✅ Pipeline de Qualidade Finalizado"

    @function
    def build_production(self, source: Directory) -> Container:
        """
        Constrói a imagem final de produção usando estratégia de COPY VENV.
        Isso garante que os executáveis (uvicorn) estejam no lugar certo.
        """
        uv_bin = dag.container().from_("ghcr.io/astral-sh/uv:latest").file("/uv")

        # --- BUILDER STAGE ---
        builder = (
            dag.container()
            .from_("python:3.12-slim")
            .with_file("/bin/uv", uv_bin)
            .with_directory("/app", source)
            .with_workdir("/app")
            # Cria um venv LIMPO para produção (sem deps de dev)
            .with_exec(["/bin/uv", "venv", "/app/.venv"])
            # Instala apenas o necessário para rodar
            .with_exec(["/bin/uv", "pip", "install", "."])
        )

        # --- RUNTIME STAGE ---
        return (
            dag.container()
            .from_("python:3.12-slim")
            .with_exec(["useradd", "-m", "appuser"])
            .with_workdir("/app")
            # 1. Copia o VENV inteiro do builder
            # Isso traz as libs E os binários (uvicorn) juntos
            .with_directory("/app/.venv", builder.directory("/app/.venv"))
            # 2. Copia o código fonte da aplicação
            .with_directory(
                "/app", 
                source, 
                exclude=["tests", "dagger-workflows", ".git", "__pycache__", ".venv"]
            )
            .with_exec(["chown", "-R", "appuser", "/app"])
            .with_user("appuser")
            # 3. Mágica do PATH: Adiciona o venv ao PATH do sistema
            .with_env_variable("PATH", "/app/.venv/bin:/usr/local/bin:/usr/bin:/bin")
            .with_env_variable("PYTHONUNBUFFERED", "1")
            .with_exposed_port(8000)
            # Agora ele vai achar o uvicorn porque está no PATH
            .with_entrypoint([
                "uvicorn", 
                "fastapi_weather.main:app", 
                "--host", "0.0.0.0", 
                "--port", "8000"
            ])
        )

    @function
    async def format(self, source: Directory) -> Directory:
        return (
            self.base(source)
            .with_exec(["uv", "run", "black", "."])
            .with_exec(["uv", "run", "ruff", "check", "--fix", "."])
            .directory("/app")
        )