import dagger
from dagger import dag, function, object_type
import time

@object_type
class Kubernetes:
    """
    Agrupa ações relacionadas ao Kubernetes
    """

    @function
    async def deploy_generic(
        self,
        source: dagger.Directory,      
        manifests: dagger.Directory,   
        kube_config: dagger.File,      
        namespace: str = "default"
    ) -> str:
        """
        Deploy Genérico: 
        1. Builda imagem.
        2. Configura kubectl para acessar o host (Colima/Docker Desktop).
        3. Aplica manifestos.
        """
        
        # --- 1. Build & Push ---
        unique_tag = f"1h-{int(time.time())}"
        image_ref = f"ttl.sh/gen-app-{unique_tag}" 
        
        print(f"🏗️  Buildando imagem: {image_ref} ...")
        
        final_ref = await (
            source
            .docker_build()
            .publish(image_ref)
        )
        print(f"📦 Imagem publicada: {final_ref}")

        # --- 2. Preparação do Container de Deploy ---
        deploy_container = (
            dag.container()
            .from_("alpine:3.18")
            .with_exec(["apk", "add", "--no-cache", "curl", "gettext", "sed"]) 
            
            # Instalação do kubectl (Multi-arch)
            .with_exec(["sh", "-c", 
                "curl -LO https://dl.k8s.io/release/v1.29.0/bin/linux/$(uname -m | sed 's/aarch64/arm64/' | sed 's/x86_64/amd64/')/kubectl"
            ])
            .with_exec(["chmod", "+x", "kubectl"])
            .with_exec(["mv", "kubectl", "/usr/local/bin/"])
            
            # --- Configuração de Rede e Kubeconfig ---
            .with_exec(["mkdir", "-p", "/root/.kube"])
            .with_mounted_file("/tmp/kubeconfig_orig", kube_config)
            .with_exec(["cp", "/tmp/kubeconfig_orig", "/root/.kube/config"])
            
            # Patch para apontar para o host
            .with_exec(["sed", "-i", "s/127.0.0.1/host.docker.internal/g", "/root/.kube/config"])
            .with_exec(["sed", "-i", "s/localhost/host.docker.internal/g", "/root/.kube/config"])

            .with_env_variable("KUBECONFIG", "/root/.kube/config")
            .with_env_variable("IMAGE_REF", final_ref)                     
        )

        # --- 3. Replace & Apply ---
        # ADICIONADO: --validate=false para evitar o erro de download do OpenAPI
        # MANTIDO: --insecure-skip-tls-verify para aceitar o certificado self-signed
        command = [
            "sh", "-c",
            f"cat /manifests/*.yaml | envsubst | kubectl apply --insecure-skip-tls-verify --validate=false -n {namespace} -f -"
        ]

        return await deploy_container.with_mounted_directory("/manifests", manifests).with_exec(command).stdout()