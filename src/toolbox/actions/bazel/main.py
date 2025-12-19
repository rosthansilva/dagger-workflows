import dagger
from dagger import object_type, function, Directory, Container, dag, File, Doc, Secret
from typing import Annotated, Optional

@object_type
class Bazel:
    """
    Ferramentas para Build e Teste com Bazel.
    Suporta autenticação via SSH e Netrc.
    """

    @function
    def base(self) -> Container:
        """
        Retorna container base com usuário 'developer'.
        """
        bazelisk_version = "v1.20.0"
        
        install_script = f"""
        ARCH=$(uname -m)
        case $ARCH in
            x86_64)  BAZEL_ARCH="amd64" ;;
            aarch64) BAZEL_ARCH="arm64" ;;
            *)       echo "Arquitetura não suportada: $ARCH"; exit 1 ;;
        esac
        
        curl -L "https://github.com/bazelbuild/bazelisk/releases/download/{bazelisk_version}/bazelisk-linux-$BAZEL_ARCH" \
             -o /usr/local/bin/bazel
        chmod +x /usr/local/bin/bazel
        """

        return (
            dag.container()
            .from_("ubuntu:22.04")
            .with_exec(["apt-get", "update"])
            # Adicionei 'openssh-client' explicitamente para o Git funcionar via SSH
            .with_exec(["apt-get", "install", "-y", "curl", "git", "build-essential", "python3", "python3-pip", "openssh-client"])
            .with_exec(["sh", "-c", install_script])
            .with_exec(["useradd", "-m", "-s", "/bin/bash", "developer"])
            .with_env_variable("BAZELISK_HOME", "/home/developer/.cache/bazelisk")
            .with_env_variable("HOME", "/home/developer")
            .with_user("developer")
            .with_workdir("/home/developer")
        )

    @function
    async def build(
        self, 
        source: Annotated[Directory, Doc("Repo raiz")], 
        targets: Annotated[list[str], Doc("Targets")] = ["//..."], 
        bzlmod: Annotated[bool, Doc("Bzlmod flag")] = True,
        bazel_version: Annotated[Optional[str], Doc("Versão específica")] = None,
        # NOVOS ARGUMENTOS DE AUTH
        ssh_key: Annotated[Optional[Secret], Doc("Chave privada SSH para clonar repos privados")] = None,
        netrc: Annotated[Optional[Secret], Doc("Arquivo .netrc para autenticação HTTP")] = None
    ) -> str:
        """Executa 'bazel build' com suporte a autenticação."""
        flags = ["build"] + targets
        if not bzlmod and self._is_version_ge_7(bazel_version):
            flags.append("--noenable_bzlmod")

        return await self._run_bazel(source, flags, bazel_version, ssh_key, netrc)

    @function
    async def test(
        self, 
        source: Annotated[Directory, Doc("Repo raiz")], 
        targets: Annotated[list[str], Doc("Targets")] = ["//..."],
        bzlmod: Annotated[bool, Doc("Bzlmod flag")] = True,
        bazel_version: Annotated[Optional[str], Doc("Versão específica")] = None,
        test_output: Annotated[str, Doc("Nível de log")] = "errors",
        # NOVOS ARGUMENTOS DE AUTH
        ssh_key: Annotated[Optional[Secret], Doc("Chave privada SSH")] = None,
        netrc: Annotated[Optional[Secret], Doc("Arquivo .netrc")] = None
    ) -> str:
        """Executa 'bazel test' com suporte a autenticação."""
        flags = ["test", f"--test_output={test_output}"] + targets
        if not bzlmod and self._is_version_ge_7(bazel_version):
            flags.append("--noenable_bzlmod")

        return await self._run_bazel(source, flags, bazel_version, ssh_key, netrc)

    @function
    def query_to_file(
        self,
        source: Annotated[Directory, Doc("Repo raiz")],
        output_name: str = "bazel_query_output.txt",
        query: str = "//...",
        bzlmod: bool = True,
        bazel_version: Optional[str] = None,
        # NOVOS ARGUMENTOS DE AUTH
        ssh_key: Annotated[Optional[Secret], Doc("Chave privada SSH")] = None,
        netrc: Annotated[Optional[Secret], Doc("Arquivo .netrc")] = None
    ) -> File:
        """Executa query com suporte a autenticação."""
        extra_flags = ""
        if not bzlmod and self._is_version_ge_7(bazel_version):
            extra_flags = "--noenable_bzlmod"

        cmd = f"bazel query '{query}' {extra_flags} > /tmp/{output_name}"

        return (
            self._setup_env(source, bazel_version, ssh_key, netrc)
            .with_exec(["sh", "-c", cmd])
            .file(f"/tmp/{output_name}")
        )

    # --- Internals ---

    def _is_version_ge_7(self, version: Optional[str]) -> bool:
        if not version: return True
        try: return int(version.split('.')[0]) >= 7
        except: return True

    async def _run_bazel(self, source: Directory, args: list[str], version: Optional[str], ssh_key: Optional[Secret], netrc: Optional[Secret]) -> str:
        return await (
            self._setup_env(source, version, ssh_key, netrc)
            .with_exec(["bazel"] + args)
            .stdout()
        )

    def _setup_env(
        self, 
        source: Directory, 
        bazel_version: Optional[str],
        ssh_key: Optional[Secret],
        netrc: Optional[Secret]
    ) -> Container:
        ctr = (
            self.base()
            .with_workdir("/src")
            .with_mounted_directory("/src", source)
            .with_mounted_cache("/home/developer/.cache/bazel", dag.cache_volume("bazel-repo-cache"), owner="developer")
            .with_mounted_cache("/home/developer/.cache/bazelisk", dag.cache_volume("bazelisk-cache"), owner="developer")
        )
        
        # 1. Configuração SSH
        if ssh_key:
            # Montamos a chave no local padrão do usuário
            ctr = ctr.with_mounted_secret("/home/developer/.ssh/id_rsa", ssh_key, owner="developer", mode=0o600)
            
            # Truque de segurança para CI: 
            # Desabilitamos o "StrictHostKeyChecking" para o git não travar perguntando se confia no github.com
            ctr = ctr.with_env_variable("GIT_SSH_COMMAND", "ssh -o StrictHostKeyChecking=no")

        # 2. Configuração Netrc
        if netrc:
            # O Bazel procura automaticamente por $HOME/.netrc
            ctr = ctr.with_mounted_secret("/home/developer/.netrc", netrc, owner="developer", mode=0o600)

        # 3. Configuração de Versão
        if bazel_version:
            ctr = ctr.with_env_variable("USE_BAZEL_VERSION", bazel_version)
            
        return ctr