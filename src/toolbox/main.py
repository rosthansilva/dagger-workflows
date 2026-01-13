import dagger
from dagger import object_type, function, Directory, Secret, Service, dag
from typing import Annotated, Optional

# --- IMPORTS CORRIGIDOS ---
from .actions.docker.main import Docker
from .actions.kubernetes.main import Kubernetes
from .actions.git_utils.main import GitUtils
from .actions.zuul.main import Zuul
from .actions.terraform.main import Terraform
from .actions.system.main import System
from .actions.python_dev.main import PythonDev
from .actions.bazel.main import Bazel
from .actions.kns.main import Kns
from .actions.dev.main import Dev

# FROMLINES


@object_type
class Toolbox:
    """
    Minha coleção central de workflows e ferramentas DevOps.
    """

    @function
    def system(self) -> System:
        """Acessa as ferramentas de sistema (echo, info, etc)."""
        return System()

    @function
    def python(self) -> PythonDev:
        return PythonDev()

    @function
    def docker(self) -> Docker:
        return Docker()

    @function
    async def up(
        self,
        source: Annotated[Directory, "Diretório raiz do projeto"],
        ignore_linting: Annotated[bool, "Se True, ignora falhas de lint e continua"] = False
    ) -> Service:
        """
        🚀 MODO DEV: Lint -> Test -> Build -> Run.
        
        Use --ignore-linting para rodar mesmo se o código estiver "feio" (black/ruff falhando).
        """
        
        print("🚦 Iniciando verificações de qualidade...")
        
        # Passamos a flag para o check_quality
        msg = await self.python().check_quality(
            source=source, 
            ignore_errors=ignore_linting
        )
        print(msg)

        # Se chegou aqui (seja porque passou ou porque ignorou), segue o baile
        print("🐳 Construindo container de produção com UV...")
        app_container = self.python().build_production(source=source)

        redis_service = (
            dag.container()
            .from_("redis:7-alpine")
            .with_exposed_port(6379)
            .as_service()
        )

        app_service = (
            app_container
            .with_service_binding("redis", redis_service)
            .with_env_variable("REDIS_URL", "redis://redis:6379")
            .with_exposed_port(8000)
            .as_service()
        )

        return app_service
    
    @function
    def bazel(self) -> Bazel:
        """
        Ferramentas para build e teste de monorepos com Bazel.
        """
        return Bazel()

    @function
    def dev(self) -> Dev:
        """Ferramentas de desenvolvimento do próprio Toolbox (scaffolding)."""
        return Dev()

    @function
    def terraform(self) -> Terraform:
        """Acessa as ferramentas de terraform."""
        return Terraform()

    @function
    def zuul(self) -> Zuul:
        """Acessa as ferramentas de zuul."""
        return Zuul()

    @function
    def git_utils(self) -> GitUtils:
        """Acessa as ferramentas de git_utils."""
        return GitUtils()

    @function
    def kubernetes(self) -> Kubernetes:
        """
        Retorna o conjunto de ações do Kubernetes
        """
        return Kubernetes()

    @function
    def kns(self) -> Kns:
        """Acessa as ferramentas de kns."""
        return Kns()
