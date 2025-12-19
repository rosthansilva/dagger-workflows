import dagger
from dagger import object_type, function, dag  # <--- IMPORTANTE: Adicione 'dag' aqui

@object_type
class System:
    """Funções utilitárias de sistema e shell."""

    @function
    def info(self) -> str:
        """Retorna informações sobre o ambiente onde o Dagger está rodando."""
        return "Executando dentro do container Dagger Linux."

    @function
    async def echo(self, message: str) -> str:
        """Repete uma mensagem."""
        # CORREÇÃO ABAIXO: De 'dagger.container()' para 'dag.container()'
        return await (
            dag.container() 
            .from_("alpine:latest")
            .with_exec(["echo", message])
            .stdout()
        )