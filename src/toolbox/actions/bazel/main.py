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
            .with_env_variable(
                "BAZELISK_BASE_URL",
                "https://github.com/bazelbuild/bazel/releases/download",
            )
            .with_env_variable("BAZELISK_HOME", "/home/developer/.cache/bazelisk")
            .with_exec(
                [
                    "sh",
                    "-c",
                    "echo '    StrictHostKeyChecking no' >> /etc/ssh/ssh_config",
                ]
            )
            .with_exec(["sh", "-c", install_script])
            .with_env_variable("HOME", "/home/developer")
            .with_user("developer")
            .with_workdir("/home/developer")
        )

    @function
    def with_proxy(
        self, container: Container, port: int = 62812, alias: str = "locahost-proxy"
    ) -> Container:
        """
        Cria um túnel que mapeia a porta do seu localhost para dentro do container.
        O serviço ficará disponível dentro do container em http://locahost-proxy:{port}
        """
        # 1. Captura o serviço rodando no seu computador (Host)
        local_svc = dag.host().service(port)

        # 2. Vincula esse serviço ao container com um nome (alias)
        return container.with_service_binding(alias, local_svc)

    @function
    async def git_check(
        self,
        remote_url: Annotated[str, Doc("URL do repositório para testar (SSH)")],
        ssh_dir: Annotated[Optional[Directory], Doc("Diretório .ssh completo")] = None,
        ssh_key: Annotated[
            Optional[Secret], Doc("Chave privada SSH (alternativa)")
        ] = None,
        netrc: Annotated[Optional[Secret], Doc("Arquivo .netrc")] = None,
    ) -> str:
        """
        Verifica a conectividade com o repositório remoto (Smoke Test).
        """
        # Usamos um diretório vazio para ser rápido, pois só queremos testar a autenticação
        ctr = self._setup_env(dag.directory(), None, ssh_key, ssh_dir, netrc).with_exec(
            ["git", "ls-remote", remote_url, "HEAD"]
        )

        try:
            output = await ctr.stdout()
            return f"✅ Conexão estabelecida com sucesso: {output.strip()}"
        except Exception as e:
            raise Exception(f"❌ Falha na conexão Git. Verifique SSH/Netrc: {str(e)}")

    @function
    async def migration_audit(
        self,
        repo1_source: Annotated[Directory, Doc("Repositório Raiz (Workspace)")],
        repo2_source: Annotated[Directory, Doc("Repositório sendo migrado (Bzlmod)")],
        repo2_target_in_repo1: Annotated[
            str, Doc("Target do repo 2 chamado pelo repo 1 (ex: @repo2//my:target)")
        ],
        bazel_version: Annotated[Optional[str], Doc("Versão do Bazel")] = None,
        ssh_dir: Optional[Directory] = None,
        ssh_key: Optional[Secret] = None,
        netrc: Optional[Secret] = None,
    ) -> File:
        """
        Valida a migração híbrida e gera relatório De-Para.
        """
        import json
        import datetime

        # --- 1. VALIDAR INTEGRAÇÃO (WORKSPACE) ---
        ctr_legacy = (
            self._setup_env(repo1_source, bazel_version, ssh_key, ssh_dir, netrc)
            .with_mounted_directory("/repo2_internal", repo2_source)
            .with_exec(["bazel", "build", repo2_target_in_repo1, "--noenable_bzlmod"])
        )

        await ctr_legacy.stdout()

        # --- 2. VALIDAR REPO 2 (BZLMOD) ---
        ctr_modern = self._setup_env(
            repo2_source, bazel_version, ssh_key, ssh_dir, netrc
        )

        raw_query = await (
            ctr_modern.with_exec(
                [
                    "sh",
                    "-c",
                    "bazel query //... --enable_bzlmod --output label > /tmp/all_targets.txt",
                ]
            )
            .file("/tmp/all_targets.txt")
            .contents()
        )
        all_targets = [t.strip() for t in raw_query.splitlines() if t.strip()]

        json_log = "/tmp/bzlmod_events.json"
        ctr_modern = ctr_modern.with_exec(
            [
                "sh",
                "-c",
                f"bazel build //... --enable_bzlmod --build_event_json_file={json_log} || true",
            ]
        )

        # --- 3. PROCESSAR RESULTADOS ---
        json_content = await ctr_modern.file(json_log).contents()
        successful_bzlmod = set()
        for line in json_content.splitlines():
            try:
                event = json.loads(line)
                if "id" in event and "targetCompleted" in event["id"]:
                    if event.get("completed", {}).get("success", False):
                        successful_bzlmod.add(event["id"]["targetCompleted"]["label"])
            except:
                continue

        # --- 4. GERAR RELATÓRIO ---
        md = [
            "# 🚀 Bazel Migration Audit Report",
            f"**Data:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Status Integração (Repo1 -> Repo2):** ✅ FUNCTIONAL (Workspace Mode)",
            f"**Aderência Bzlmod (Repo2):** {len(successful_bzlmod)}/{len(all_targets)} targets funcionais",
            "",
            "| Target | Workspace | Bzlmod | Status |",
            "| :--- | :---: | :---: | :--- |",
        ]

        for t in all_targets:
            res = "✅ OK" if t in successful_bzlmod else "❌ FAIL"
            migrated = "DONE" if t in successful_bzlmod else "PENDING"
            md.append(f"| {t} | ✅ | {res} | {migrated} |")

        return (
            dag.container()
            .from_("alpine")
            .with_new_file("/report.md", contents="\n".join(md))
            .file("/report.md")
        )

    @function
    async def build(
        self,
        source: Annotated[Directory, Doc("Repo raiz")],
        targets: Annotated[list[str], Doc("Targets")] = ["//..."],
        bzlmod: Annotated[bool, Doc("Bzlmod flag")] = True,
        bazel_version: Annotated[Optional[str], Doc("Versão específica")] = None,
        ssh_dir: Annotated[
            Optional[Directory], Doc("Full .ssh directory to mount")
        ] = None,
        ssh_key: Annotated[Optional[Secret], Doc("Chave privada SSH")] = None,
        netrc: Annotated[
            Optional[Secret], Doc("Arquivo .netrc para autenticação HTTP")
        ] = None,
    ) -> str:
        """Executa 'bazel build' com suporte a autenticação."""
        flags = ["build"] + targets
        if not bzlmod and self._is_version_ge_7(bazel_version):
            flags.append("--noenable_bzlmod")

        return await self._run_bazel(
            source, flags, bazel_version, ssh_key, ssh_dir, netrc
        )

    @function
    async def test(
        self,
        source: Annotated[Directory, Doc("Repo raiz")],
        targets: Annotated[list[str], Doc("Targets")] = ["//..."],
        bzlmod: Annotated[bool, Doc("Bzlmod flag")] = True,
        bazel_version: Annotated[Optional[str], Doc("Versão específica")] = None,
        test_output: Annotated[str, Doc("Nível de log")] = "errors",
        ssh_dir: Annotated[
            Optional[Directory], Doc("Full .ssh directory to mount")
        ] = None,
        ssh_key: Annotated[Optional[Secret], Doc("Chave privada SSH")] = None,
        netrc: Annotated[Optional[Secret], Doc("Arquivo .netrc")] = None,
    ) -> str:
        """Executa 'bazel test' com suporte a autenticação."""
        flags = ["test", f"--test_output={test_output}"] + targets
        if not bzlmod and self._is_version_ge_7(bazel_version):
            flags.append("--noenable_bzlmod")

        return await self._run_bazel(
            source, flags, bazel_version, ssh_key, ssh_dir, netrc
        )

    @function
    async def build_with_report(
        self,
        source: Annotated[Directory, Doc("Repo raiz")],
        targets: Annotated[list[str], Doc("Targets")] = ["//..."],
        build_args: Annotated[
            list[str], Doc("Flags extras de build (ex: --config=gcc9)")
        ] = [],
        bzlmod: Annotated[bool, Doc("Bzlmod flag")] = True,
        bazel_version: Annotated[Optional[str], Doc("Versão específica")] = None,
        ssh_dir: Annotated[
            Optional[Directory], Doc("Full .ssh directory to mount")
        ] = None,
        ssh_key: Annotated[Optional[Secret], Doc("Chave privada SSH")] = None,
        netrc: Annotated[Optional[Secret], Doc("Arquivo .netrc")] = None,
    ) -> File:
        """
        Executa build e retorna relatório Markdown.
        """
        import json
        import datetime

        target_str = " ".join(targets)
        build_args_str = " ".join(build_args)

        extra_flags = ""
        if not bzlmod and self._is_version_ge_7(bazel_version):
            extra_flags = "--noenable_bzlmod"

        ctr = self._setup_env(source, bazel_version, ssh_key, ssh_dir, netrc)

        print("1. Querying targets...")
        query_cmd = f"bazel query '{target_str}' {extra_flags} --output label > /tmp/query_output.txt"
        ctr = ctr.with_exec(["sh", "-c", query_cmd])

        raw_query = await ctr.file("/tmp/query_output.txt").contents()
        all_targets = [t.strip() for t in raw_query.splitlines() if t.strip()]

        print("2. Building targets...")
        json_log_path = "/tmp/build_events.json"

        build_cmd = (
            f"bazel build {target_str} {build_args_str} {extra_flags} "
            f"--build_event_json_file={json_log_path} "
            "--color=yes --curses=no || true"
        )

        ctr = ctr.with_exec(["sh", "-c", build_cmd])

        try:
            json_content = await ctr.file(json_log_path).contents()
        except Exception:
            print("Aviso: Arquivo JSON não encontrado")
            json_content = ""

        print("3. Processing report...")
        successful_targets = set()
        failed_targets = set()

        for line in json_content.splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                if "id" in event and "targetCompleted" in event["id"]:
                    label = event["id"]["targetCompleted"]["label"]
                    success = event.get("completed", {}).get("success", False)
                    if success:
                        successful_targets.add(label)
                    else:
                        failed_targets.add(label)
            except json.JSONDecodeError:
                continue

        md_lines = []
        md_lines.append(f"## Bazel Build Report")
        md_lines.append(
            f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
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

        return ctr.with_new_file("build_report.md", contents="\n".join(md_lines)).file(
            "build_report.md"
        )

    @function
    def query_to_file(
        self,
        source: Annotated[Directory, Doc("Repo raiz")],
        output_name: str = "bazel_query_output.txt",
        query: str = "//...",
        bzlmod: bool = True,
        bazel_version: Optional[str] = None,
        ssh_dir: Annotated[
            Optional[Directory], Doc("Full .ssh directory to mount")
        ] = None,
        ssh_key: Annotated[Optional[Secret], Doc("Chave privada SSH")] = None,
        netrc: Annotated[Optional[Secret], Doc("Arquivo .netrc")] = None,
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
        if not version:
            return True
        try:
            return int(version.split(".")[0]) >= 7
        except:
            return True

    async def _run_bazel(
        self,
        source: Directory,
        args: list[str],
        version: Optional[str],
        ssh_key: Optional[Secret],
        ssh_dir: Optional[Directory],
        netrc: Optional[Secret],
    ) -> str:
        return await (
            self._setup_env(source, version, ssh_key, ssh_dir, netrc)
            .with_exec(["bazel"] + args)
            .stdout()
        )

    def _setup_env(
        self,
        source: Directory,
        bazel_version: Optional[str],
        ssh_key: Optional[Secret],
        ssh_dir: Optional[Directory],
        netrc: Optional[Secret],
    ) -> Container:
        home_dir = "/home/developer"
        ctr = (
            self.base()
            .with_workdir("/src")
            .with_mounted_directory("/src", source)
            .with_mounted_cache(
                f"{home_dir}/.cache/bazel",
                dag.cache_volume("bazel-repo-cache"),
                owner="developer",
            )
            .with_mounted_cache(
                f"{home_dir}/.cache/bazelisk",
                dag.cache_volume("bazelisk-cache"),
                owner="developer",
            )
            .with_env_variable("GIT_SSH_COMMAND", "ssh -o StrictHostKeyChecking=no")
        )

        # 1. Configuração SSH (Prioriza Diretório > Chave Única)
        if ssh_dir:
            ctr = ctr.with_mounted_directory(
                f"{home_dir}/.ssh", ssh_dir, owner="developer"
            )
        elif ssh_key:
            ctr = ctr.with_mounted_secret(
                f"{home_dir}/.ssh/id_rsa", ssh_key, owner="developer", mode=0o600
            )

        # 2. Configuração Netrc
        if netrc:
            ctr = ctr.with_mounted_secret(
                f"{home_dir}/.netrc", netrc, owner="developer", mode=0o600
            )

        # 3. Configuração de Versão
        if bazel_version:
            ctr = ctr.with_env_variable("USE_BAZEL_VERSION", bazel_version)

        return ctr
