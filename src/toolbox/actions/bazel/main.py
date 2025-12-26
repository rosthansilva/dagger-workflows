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
        apt-get update && apt-get install -y curl git build-essential python3 python3-pip openssh-client jq
        """

        return (
            dag.container()
            .from_("ubuntu:22.04")
            .with_exec(["apt-get", "update"])
            # Adicionei 'openssh-client' explicitamente para o Git funcionar via SSH
            .with_exec(["sh", "-c", install_script])
            .with_exec(["useradd", "-m", "-s", "/bin/bash", "developer"])
            .with_env_variable("BAZELISK_HOME", "/home/developer/.cache/bazelisk")
            .with_exec(["sh", "-c", "echo '    StrictHostKeyChecking no' >> /etc/ssh/ssh_config"])
            .with_exec(["sh", "-c", install_script])
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
        ssh_dir: Annotated[Optional[Directory], Doc("Full .ssh directory to mount")] = None,
        ssh_key: Annotated[Optional[Secret], Doc("Chave privada SSH")] = None,
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
        ssh_dir: Annotated[Optional[Directory], Doc("Full .ssh directory to mount")] = None,
        ssh_key: Annotated[Optional[Secret], Doc("Chave privada SSH")] = None,
        netrc: Annotated[Optional[Secret], Doc("Arquivo .netrc")] = None
    ) -> str:
        """Executa 'bazel test' com suporte a autenticação."""
        flags = ["test", f"--test_output={test_output}"] + targets
        if not bzlmod and self._is_version_ge_7(bazel_version):
            flags.append("--noenable_bzlmod")

        return await self._run_bazel(source, flags, bazel_version, ssh_key, netrc)

    @function
    async def build_with_report(
        self,
        source: Annotated[Directory, Doc("Repo raiz")],
        targets: Annotated[list[str], Doc("Targets")] = ["//..."],
        # NOVO: Separamos configs (como --config=gcc9) dos targets para não quebrar o 'bazel query'
        build_args: Annotated[list[str], Doc("Flags extras de build (ex: --config=gcc9)")] = [],
        bzlmod: Annotated[bool, Doc("Bzlmod flag")] = True,
        bazel_version: Annotated[Optional[str], Doc("Versão específica")] = None,
        ssh_dir: Annotated[Optional[Directory], Doc("Full .ssh directory to mount")] = None,
        ssh_key: Annotated[Optional[Secret], Doc("Chave privada SSH")] = None,
        netrc: Annotated[Optional[Secret], Doc("Arquivo .netrc")] = None
    ) -> File:
        """
        Executa build e retorna relatório Markdown. 
        Processa o JSON internamente no Dagger SDK (host), sem scripts injetados no container.
        """
        
        # 1. Preparar Strings
        target_str = " ".join(targets)      # ex: "//..."
        build_args_str = " ".join(build_args) # ex: "--config=gcc9"
        
        extra_flags = ""
        if not bzlmod and self._is_version_ge_7(bazel_version):
            extra_flags = "--noenable_bzlmod"

        # 2. Configurar Container
        ctr = self._setup_env(source, bazel_version, ssh_key, ssh_dir, netrc)
        
        # 3. Executar Query (SOMENTE TARGETS)
        # Importante: Não passamos 'build_args' aqui, pois 'bazel query' não suporta --config
        print("1. Querying targets...")
        query_cmd = f"bazel query '{target_str}' {extra_flags} --output label > /tmp/query_output.txt"
        ctr = ctr.with_exec(["sh", "-c", query_cmd])
        
        # Trazemos o resultado para a memória do Python (Host)
        raw_query = await ctr.file("/tmp/query_output.txt").contents()
        all_targets = [t.strip() for t in raw_query.splitlines() if t.strip()]

        # 4. Executar Build (TARGETS + BUILD_ARGS)
        # Aqui sim passamos o --config=gcc9
        print("2. Building targets...")
        json_log_path = "/tmp/build_events.json"
        
        # '|| true' impede que o Dagger pare se houver erro de compilação (queremos gerar o relatório mesmo assim)
        build_cmd = (
            f"bazel build {target_str} {build_args_str} {extra_flags} "
            f"--build_event_json_file={json_log_path} "
            "--color=yes --curses=no || true"
        )
        
        ctr = ctr.with_exec(["sh", "-c", build_cmd])
        
        # Ler o JSON gerado
        try:
            json_content = await ctr.file(json_log_path).contents()
        except Exception:
            print("Aviso: Arquivo JSON não encontrado (Build falhou antes de iniciar?)")
            json_content = ""

        # 5. Processamento Lógico (Python Puro no Host)
        print("3. Processing report...")
        successful_targets = set()
        failed_targets = set()

        for line in json_content.splitlines():
            if not line.strip(): continue
            try:
                event = json.loads(line)
                if 'id' in event and 'targetCompleted' in event['id']:
                    label = event['id']['targetCompleted']['label']
                    success = event.get('completed', {}).get('success', False)
                    if success:
                        successful_targets.add(label)
                    else:
                        failed_targets.add(label)
            except json.JSONDecodeError:
                continue

        # 6. Gerar Markdown
        md_lines = []
        md_lines.append(f"## Bazel Build Report")
        md_lines.append(f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md_lines.append("")
        md_lines.append("| Target | Status | Details |")
        md_lines.append("| :--- | :--- | :--- |")

        for target in all_targets:
            if target in successful_targets:
                status = "✅ SUCCESS"
                detail = "Build successful"
            elif target in failed_targets:
                status = "❌ FAILED"
                detail = "Compilation or Test failed"
            else:
                status = "⚪ SKIPPED"
                detail = "Dependency failed or not attempted"
            
            md_lines.append(f"| {target} | {status} | {detail} |")

        # Retornar arquivo
        return ctr.with_new_file("build_report.md", contents="\n".join(md_lines)).file("build_report.md")
        
    @function
    def query_to_file(
        self,
        source: Annotated[Directory, Doc("Repo raiz")],
        output_name: str = "bazel_query_output.txt",
        query: str = "//...",
        bzlmod: bool = True,
        bazel_version: Optional[str] = None,
        ssh_dir: Annotated[Optional[Directory], Doc("Full .ssh directory to mount")] = None,
        ssh_key: Annotated[Optional[Secret], Doc("Chave privada SSH")] = None,
        netrc: Annotated[Optional[Secret], Doc("Arquivo .netrc")] = None
    ) -> File:
        """Executa query com suporte a autenticação."""
        extra_flags = ""
        if not bzlmod and self._is_version_ge_7(bazel_version):
            extra_flags = "--noenable_bzlmod"

        cmd = f"bazel query '{query}' {extra_flags} > /tmp/{output_name}"

        return (
            self._setup_env(source, bazel_version, ssh_key, ssh_dir, netrc)
            .with_exec(["sh", "-c", cmd])
            .file(f"/tmp/{output_name}")
        )

    # --- Internals ---

    def _is_version_ge_7(self, version: Optional[str]) -> bool:
        if not version: return True
        try: return int(version.split('.')[0]) >= 7
        except: return True

    async def _run_bazel(self, source: Directory, args: list[str], version: Optional[str], ssh_key: Optional[Secret], ssh_dir: Optional[Secret], netrc: Optional[Secret]) -> str:
        return await (
            self._setup_env(source, version, ssh_dir, netrc)
            .with_exec(["bazel"] + args)
            .stdout()
        )

    def _setup_env(
        self, 
        source: Directory, 
        bazel_version: Optional[str],
        ssh_key: Optional[Secret],
        ssh_dir: Optional[Directory],
        netrc: Optional[Secret]
    ) -> Container:
        home_dir = "/home/developer"
        ctr = (
            self.base()
            .with_workdir("/src")
            .with_mounted_directory("/src", source)
            .with_mounted_cache("/home/developer/.cache/bazel", dag.cache_volume("bazel-repo-cache"), owner="developer")
            .with_mounted_cache("/home/developer/.cache/bazelisk", dag.cache_volume("bazelisk-cache"), owner="developer")
        )
        # Configure SSH DIR
        if ssh_dir:
            ctr = ctr.with_mounted_directory(f"{home_dir}/.ssh", ssh_dir, owner="developer")

        if netrc:
            ctr = ctr.with_mounted_secret(f"{home_dir}/.netrc", netrc, owner="developer", mode=0o600)
        # Configuração SSH
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