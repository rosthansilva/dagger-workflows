import dagger
from dagger import dag, function, object_type


@object_type
class CustomKindCluster:
    """
    Representa o estado de um cluster Kind Customizado rodando.
    """

    dind_service: dagger.Service
    kube_config: dagger.File

    @function
    def terminal(self) -> dagger.Container:
        """
        Retorna um container kubectl conectado a este cluster.
        """
        return (
            dag.container()
            .from_("bitnami/kubectl:latest")
            .with_user("root")
            .with_service_binding("docker-host", self.dind_service)
            .with_file("/root/.kube/config", self.kube_config)
            # Patch de Rede
            .with_exec(["sed", "-i", "s/0.0.0.0/docker-host/g", "/root/.kube/config"])
            .with_exec(["sed", "-i", "s/127.0.0.1/docker-host/g", "/root/.kube/config"])
            .with_exec(["sed", "-i", "s/localhost/docker-host/g", "/root/.kube/config"])
            .with_env_variable("KUBECONFIG", "/root/.kube/config")
            .with_exec(
                [
                    "kubectl",
                    "wait",
                    "--for=condition=Ready",
                    "nodes",
                    "--all",
                    "--timeout=5m",
                ]
            )
            .with_default_args(["sh"])
        )


@object_type
class CustomKind:
    """
    Gerenciador para criar clusters Kind com configurações avançadas.
    """

    @function
    def create(self) -> CustomKindCluster:
        # Configuração YAML
        kind_config = """
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
networking:
  apiServerAddress: "0.0.0.0"
  apiServerPort: 6443
kubeadmConfigPatches:
  - |
    apiVersion: kubelet.config.k8s.io/v1beta1
    kind: KubeletConfiguration
    evictionHard:
      nodefs.available: "0%"
kubeadmConfigPatchesJSON6902:
  - group: kubeadm.k8s.io
    version: v1beta3
    kind: ClusterConfiguration
    patch: |
      - op: add
        path: /apiServer/certSANs/-
        value: my-hostname
nodes:
  - role: control-plane
    extraPortMappings:
      - containerPort: 80
        hostPort: 80
      - containerPort: 443
        hostPort: 443
  - role: worker
"""

        # Serviço Docker-in-Docker (DinD)
        # Requer Dagger v0.12+ (engine atualizada) para 'with_security_context'
        dind_service = (
            dag.container()
            .from_("docker:24-dind")
            .with_env_variable("DOCKER_TLS_CERTDIR", "")
            .with_exposed_port(6443)
            .with_exposed_port(80)
            .with_exposed_port(443)
            .with_exec(["dockerd-entrypoint.sh", "--tls=false"])
            .as_service()
        )

        # Container Bootstrap
        # AQUI ESTÁ A LÓGICA DE DETECÇÃO DE ARQUITETURA ATUALIZADA
        bootstrap = (
            dag.container()
            .from_("alpine:3.18")
            .with_user("root")
            .with_exec(["apk", "add", "--no-cache", "curl", "docker-cli"])
            .with_exec(
                [
                    "sh",
                    "-c",
                    """
                # Detecta arquitetura e normaliza para (amd64 ou arm64)
                ARCH=$(uname -m | sed -e 's/x86_64/amd64/' -e 's/aarch64/arm64/')
                
                echo "Detected Architecture: $ARCH"
                
                # Baixa a versão v0.31.0 específica para Linux e a arquitetura detectada
                curl -Lo /usr/local/bin/kind "https://kind.sigs.k8s.io/dl/v0.31.0/kind-linux-${ARCH}"
                
                chmod +x /usr/local/bin/kind
            """,
                ]
            )
            .with_service_binding("docker-host", dind_service)
            .with_env_variable("DOCKER_HOST", "tcp://docker-host:2375")
            .with_new_file("/kind-config.yaml", kind_config)
            # Sleep para garantir que o dockerd subiu
            .with_exec(["sh", "-c", "docker ps"])
            .with_exec(
                [
                    "sh",
                    "-c",
                    "sleep 5 && kind create cluster --config /kind-config.yaml",
                ]
            )
            .with_exec(["kind", "get", "kubeconfig"], redirect_stdout="/tmp/kubeconfig")
        )

        return CustomKindCluster(dind_service=dind_service, kube_config=bootstrap.file("/tmp/kubeconfig"))
