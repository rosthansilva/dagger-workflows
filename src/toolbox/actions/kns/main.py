import dagger
from dagger import object_type, function, dag, Doc
from typing import Annotated, Optional

# Ajuste o import conforme sua estrutura de pastas
from ..kubernetes.main import Kubernetes


@object_type
class Kns:
    """
    Gerenciamento de cluster de teste K3s.
    """

    @function
    def service(self) -> dagger.Service:
        # MANTENHA O ORIGINAL (Só expõe a API 6443)
        k3s_container = dag.k3_s("test").container()
        k3s_container = k3s_container.with_mounted_cache("/var/lib/dagger", dag.cache_volume("varlibdagger"))
        k3s_container = k3s_container.with_exposed_port(6443)
        return dag.k3_s("test").with_container(k3s_container).server()

    @function
    def get_config(self) -> dagger.File:
        """
        Retorna o kubeconfig para acesso via host.
        Use: dagger call kns get-config export --path ./kubeconfig.yaml
        """
        # local=True é essencial para acessar de fora do container (localhost)
        return dag.k3_s("test").config(local=True)

    @function
    async def reset(self) -> str:
        """
        MATAR/RESETAR: Limpa os dados do cluster.
        Como o 'service up' apenas para com Ctrl+C mas mantem os dados,
        use isso para destruir o estado do cluster.
        """
        await (
            dag.container()
            .from_("alpine:latest")
            .with_mounted_cache("/var/lib/dagger", dag.cache_volume("varlibdagger"))
            .with_exec(["sh", "-c", "rm -rf /var/lib/dagger/*"])
            .sync()
        )
        return "🔥 Cluster destruído (dados limpos). Próximo 'up' será do zero."

    @function
    async def kns_internal(self) -> dagger.Container:
        """
        Se você realmente quiser rodar o k9s DE DENTRO do Dagger enquanto o cluster sobe.
        Isso ainda vai matar o cluster quando você sair.
        """
        await self.service().start()
        return dag.k3_s("test").kns().terminal()

    @function
    async def kubectl(
        self, command: Annotated[str, Doc("O comando kubectl a ser executado. Ex: 'get pods -A'")]
    ) -> str:
        """
        Roda um comando kubectl diretamente contra este cluster (internamente).
        Não requer que o cluster esteja exposto no host via 'service up'.
        """
        client = Kubernetes()
        cluster_svc = self.service()
        kube_config = self.get_config()

        return await client.run_kubectl(kube_config=kube_config, command=command, cluster_service=cluster_svc)

    @function
    def gateway(self) -> dagger.Service:
        """
        Retorna um serviço Proxy que expõe a API (6443) e o Ingress (80/443).
        Use isso para acessar aplicações rodando dentro do K3s.

        Comando: dagger call kns gateway up --ports 6443:6443 --ports 80:80 --ports 443:443
        """
        # 1. Pegamos o serviço original do K3s
        k3s_svc = self.service()

        # 2. Inicializamos o Proxy
        # O módulo proxy permite adicionar múltiplos serviços ou portas
        proxy = dag.proxy()

        # 3. Configuramos as rotas (Forwarding)

        # Rota API: Host 6443 -> K3s 6443
        proxy = proxy.with_service(service=k3s_svc, name="k8s-api", frontend=6443, backend=6443)

        # Rota Ingress HTTP: Host 80 -> K3s 80
        proxy = proxy.with_service(service=k3s_svc, name="ingress-http", frontend=80, backend=80)

        # Rota Ingress HTTPS: Host 443 -> K3s 443
        proxy = proxy.with_service(service=k3s_svc, name="ingress-https", frontend=443, backend=443)

        # 4. Retornamos o serviço do Proxy
        return proxy.service()

    @function
    async def test_internal_connection(self) -> str:
        """
        Testa a conexão entre o Cliente Kubernetes e este Cluster KNS
        rodando tudo internamente no Dagger.
        """
        k8s_client = Kubernetes()
        my_service = self.service()
        my_config = self.get_config()

        result = await k8s_client.run_kubectl(
            kube_config=my_config, command="get nodes -o wide", cluster_service=my_service
        )

        return f"🎉 Sucesso! O cliente Kubernetes viu o cluster KNS:\n\n{result}"
