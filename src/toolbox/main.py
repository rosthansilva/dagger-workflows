import dagger
from dagger import object_type, function

# ALTERAÇÃO AQUI:
# Usamos o ponto (.) para indicar "deste pacote atual, vá para actions..."
# Isso remove a dependência do nome "src"
from .actions.system.main import System
from .actions.python_dev.main import PythonDev
from .actions.bazel.main import Bazel

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
        """Acessa as ferramentas de desenvolvimento Python (lint, test)."""
        return PythonDev()
    
    @function
    def bazel(self) -> Bazel:
        """
        Ferramentas para build e teste de monorepos com Bazel.
        Suporta cenários de migração Workspace/Bzlmod.
        """
        return Bazel()