import dagger
from dagger import dag, function, object_type
import re
import shlex
from typing import Optional, List


@object_type
class Kubernetes:
    """
    Cliente Kubernetes Universal.
    """

    @function
    async def run_kubectl(
        self,
        kube_config: dagger.File,
        command: str,
        extra_hosts: Optional[List[str]] = None,
        cluster_service: Optional[dagger.Service] = None,
    ) -> str:
        hosts = extra_hosts or []
        container = await self._setup_client_container(kube_config, hosts, cluster_service)

        cmd_args = shlex.split(command)
        # Adicionamos flag para evitar erro de x509 em ambiente de dev
        full_cmd = ["kubectl", "--insecure-skip-tls-verify"] + cmd_args

        return await container.with_exec(full_cmd).stdout()

    @function
    async def apply_manifests(
        self,
        kube_config: dagger.File,
        manifests: dagger.Directory,
        namespace: str = "default",
        extra_hosts: Optional[List[str]] = None,
        cluster_service: Optional[dagger.Service] = None,
    ) -> str:
        hosts = extra_hosts or []
        container = await self._setup_client_container(kube_config, hosts, cluster_service)

        cmd = ["sh", "-c", f"kubectl apply --insecure-skip-tls-verify -n {namespace} -f /manifests/"]

        return await container.with_mounted_directory("/manifests", manifests).with_exec(cmd).stdout()

    # --- LÓGICA CENTRAL ---
    async def _setup_client_container(
        self,
        kube_config: dagger.File,
        extra_hosts: List[str],
        cluster_service: Optional[dagger.Service] = None,
    ) -> dagger.Container:

        ctr = (
            dag.container()
            .from_("bitnami/kubectl:latest")
            .with_user("root")
            .with_exec(["mkdir", "-p", "/root/.kube"])
            .with_mounted_file("/tmp/kubeconfig_orig", kube_config)
            .with_exec(["cp", "/tmp/kubeconfig_orig", "/root/.kube/config"])
            .with_env_variable("KUBECONFIG", "/root/.kube/config")
        )

        if extra_hosts:
            for host_entry in extra_hosts:
                ctr = ctr.with_exec(["sh", "-c", f"echo '{host_entry}' >> /etc/hosts"])

        config_content = await kube_config.contents()

        # Regex para capturar porta do localhost/127.0.0.1
        local_match = re.search(r"server: https://(?:127\.0\.0\.1|localhost):(\d+)", config_content)

        # CENÁRIO A: K3s interno (Service Binding explícito - vindo do 'kns')
        if cluster_service:
            ctr = ctr.with_service_binding("k3s-server", cluster_service)
            ctr = ctr.with_exec(["sed", "-i", "s/127.0.0.1/k3s-server/g", "/root/.kube/config"])
            ctr = ctr.with_exec(["sed", "-i", "s/localhost/k3s-server/g", "/root/.kube/config"])

        # CENÁRIO B: Cluster Local (Host Service - rodando na sua máquina)
        elif local_match:
            try:
                port = int(local_match.group(1))
                tunnel_alias = "host.docker.internal"

                # AQUI OCORRIA O ERRO: dag.host() requer SDK atualizado
                host_svc = dag.host().service(ports=[dagger.PortForward(backend=port, frontend=port)])

                ctr = ctr.with_service_binding(tunnel_alias, host_svc)
                ctr = ctr.with_exec(["sed", "-i", f"s/127.0.0.1/{tunnel_alias}/g", "/root/.kube/config"])
                ctr = ctr.with_exec(["sed", "-i", f"s/localhost/{tunnel_alias}/g", "/root/.kube/config"])
            except AttributeError as e:
                # Fallback ou mensagem de erro mais clara
                raise Exception(
                    f"Erro ao acessar dag.host(). Verifique se 'dagger-io' está atualizado no pyproject.toml. Detalhe: {e}"
                )

        return ctr
