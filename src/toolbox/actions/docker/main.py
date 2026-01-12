import dagger
from dagger import object_type, function, Directory, Container, dag, File, Doc, Secret
from typing import Annotated, Optional


@object_type
class Docker:
    """
    Ferramentas robustas para operações com Docker.
    Gerencia Builds, Escaneamento de Vulnerabilidades e Publicação em Registros.
    """

    @function
    def base(self) -> Container:
        """
        Retorna um container com ferramentas auxiliares (Docker CLI, Trivy para scan).
        """
        return (
            dag.container()
            .from_("alpine:latest")
            .with_exec(["apk", "add", "--no-cache", "docker-cli", "bash", "curl"])
        )

    @function
    def build(
        self,
        source: Annotated[Directory, Doc("Diretório de contexto para a build")],
        dockerfile: Annotated[
            str, Doc("Caminho relativo para o Dockerfile")
        ] = "Dockerfile",
        target: Annotated[Optional[str], Doc("Target stage específico")] = None,
        build_args: Annotated[
            Optional[list[str]], Doc("Build args no formato ['NAME=VALUE']")
        ] = None,
        platforms: Annotated[
            Optional[list[str]], Doc("Lista de plataformas (ex: linux/amd64)")
        ] = None,
    ) -> Container:
        """
        Executa o 'docker build' utilizando a engine nativa do Dagger.
        Retorna o container resultante para inspeção ou publicação.
        """
        # Conversão de build args para o formato do SDK
        args = []
        if build_args:
            for item in build_args:
                name, value = item.split("=", 1)
                args.append(dagger.BuildArg(name=name, value=value))

        # O Dagger gerencia o cache de camadas automaticamente via Cache Volume interno
        return source.docker_build(
            dockerfile=dockerfile,
            target=target or "",
            build_args=args,
            # platforms=platforms # Habilitar se usar multi-platform nodes
        )

    @function
    async def push(
        self,
        container: Annotated[Container, Doc("O container buildado")],
        address: Annotated[str, Doc("Endereço completo da imagem (ex: user/repo:tag)")],
        username: Annotated[Optional[str], Doc("Usuário do Registry")] = None,
        secret: Annotated[
            Optional[Secret], Doc("Secret (Password/Token) do Registry")
        ] = None,
    ) -> str:
        """
        Faz o push de um container para um registro remoto com autenticação via Secret.
        """
        if username and secret:
            # Determinamos o domínio do registro para a autenticação
            # Se não houver '.' no primeiro segmento, assume-se Docker Hub
            registry_host = "index.docker.io"
            if "/" in address:
                first_part = address.split("/")[0]
                if "." in first_part:
                    registry_host = first_part

            # Autentica no HOST do registro, mas publica no ADDRESS completo
            container = container.with_registry_auth(registry_host, username, secret)

        return await container.publish(address)

    @function
    async def scan_report(
        self,
        container: Annotated[Container, Doc("O container a ser analisado")],
        severity: Annotated[
            str, Doc("Severidade mínima (LOW,MEDIUM,HIGH,CRITICAL)")
        ] = "HIGH",
        exit_code: Annotated[
            int, Doc("1 para falhar o build se houver vulnerabilidades")
        ] = 0,
    ) -> File:
        """
        Realiza scan de segurança usando Trivy e gera um relatório Markdown.
        """
        tarball = container.as_tarball()

        scan_ctr = (
            dag.container()
            .from_("aquasec/trivy:latest")
            .with_mounted_file("/tmp/image.tar", tarball)
            .with_exec(
                [
                    "trivy",
                    "image",  # <--- ADICIONADO "trivy" AQUI
                    "--input",
                    "/tmp/image.tar",
                    "--format",
                    "table",
                    "--severity",
                    severity,
                    "--exit-code",
                    str(exit_code),
                ]
            )
        )

        report_content = await scan_ctr.stdout()

        return (
            dag.container()
            .from_("alpine")
            .with_new_file("/report.txt", contents=report_content)
            .file("/report.txt")
        )

    @function
    async def dive_summary(
        self,
        container: Annotated[
            Container, Doc("O container para analisar eficiência de camadas")
        ],
    ) -> str:
        """
        Analisa a eficiência da imagem (camadas desperdiçadas) usando o Dive.
        """
        tarball = container.as_tarball()

        return await (
            dag.container()
            .from_("wagoodman/dive:latest")
            .with_mounted_file("/tmp/image.tar", tarball)
            .with_env_variable("CI", "true")
            .with_exec(["dive", "--source", "docker-archive", "/tmp/image.tar"])
            .stdout()
        )

    @function
    def export_to_host(
        self,
        container: Annotated[Container, Doc("O container a ser exportado")],
        path: Annotated[str, Doc("Caminho no host (ex: ./my-image.tar)")] = "image.tar",
    ) -> File:
        """
        Exporta a imagem para o host em formato .tar para uso manual com 'docker load'.
        """
        return container.as_tarball()

    @function
    async def full_cycle(
        self,
        source: Annotated[Directory, Doc("Diretório de contexto para a build")],
        address: Annotated[str, Doc("Endereço completo da imagem (ex: user/repo:tag)")],
        dockerfile: Annotated[str, Doc("Caminho para o Dockerfile")] = "Dockerfile",
        username: Annotated[Optional[str], Doc("Usuário do Registry")] = None,
        secret: Annotated[Optional[Secret], Doc("Secret do Registry")] = None,
        skip_scan: Annotated[bool, Doc("Se True, pula o scan de segurança")] = False,
    ) -> str:
        """
        Ciclo Completo Docker: Build -> Scan (opcional) -> Push.
        Retorna o digest da imagem publicada.
        """
        # 1. Build
        print(f"🔨 Iniciando build da imagem para: {address}...")
        container = self.build(source=source, dockerfile=dockerfile)

        # 2. Security Scan (Interrompe se houver vulnerabilidades CRITICAL)
        if not skip_scan:
            print("🛡️  Rodando scan de segurança (Trivy)...")
            # Usamos exit_code=1 para que o Dagger lance uma exceção se encontrar falhas graves
            await self.scan_report(
                container=container, severity="CRITICAL", exit_code=1
            )
            print("✅ Scan limpo! Nenhuma vulnerabilidade crítica encontrada.")

        # 3. Push
        print(f"🚀 Publicando imagem em {address}...")
        image_digest = await self.push(
            container=container, address=address, username=username, secret=secret
        )

        return f"🚀 Ciclo finalizado com sucesso!\nDigest: {image_digest}"
