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
            .with_exec(["apt-get", "install", "-y", "curl", "git", "build-essential", "python3", "python3-pip", "openssh-client", "jq"])
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
    def build_with_report(
        self,
        source: Annotated[Directory, Doc("Root repo")],
        targets: Annotated[list[str], Doc("Targets")] = ["//..."],
        bzlmod: Annotated[bool, Doc("Bzlmod flag")] = True,
        bazel_version: Annotated[Optional[str], Doc("Specific version")] = None,
        ssh_dir: Annotated[Optional[Directory], Doc("Full .ssh directory to mount")] = None,
        ssh_key: Annotated[Optional[Secret], Doc("SSH Private Key")] = None,
        netrc: Annotated[Optional[Secret], Doc(".netrc file")] = None
    ) -> File:
        """
        Executes build and returns a Markdown file (build_report.md)
        listing successful, failed, and skipped targets.
        """
        
        # 1. Prepare flags for the python script
        target_str = " ".join(targets)
        extra_flag = ""
        if not bzlmod and self._is_version_ge_7(bazel_version):
            extra_flag = "--noenable_bzlmod"

        # 2. The Python Script to inject into the container
        # This script runs 'bazel query' first, then 'bazel build', 
        # parses the JSON event stream, and writes the Markdown file.
        python_script = f"""
import subprocess
import json
import sys
import datetime

JSON_LOG = "build_events.json"
REPORT_FILE = "build_report.md"
TARGETS = "{target_str}"
EXTRA_FLAGS = "{extra_flag}"

def generate_report():
    print(f"--- Starting Build Report Generation ---")
    
    # Step 1: Get the list of ALL intended targets via query
    print("1. Querying targets...")
    try:
        # We split flags manually just in case EXTRA_FLAGS is empty
        query_cmd = ["bazel", "query", TARGETS, "--output", "label"]
        if EXTRA_FLAGS:
            query_cmd.insert(2, EXTRA_FLAGS)
            
        raw_query = subprocess.check_output(query_cmd).decode("utf-8")
        all_targets = [t.strip() for t in raw_query.splitlines() if t.strip()]
    except subprocess.CalledProcessError as e:
        print(f"Error querying targets: {{e}}")
        sys.exit(1)

    # Step 2: Run the build and generate BEP JSON
    # We use check=False because we expect build failures (we want to report them, not crash)
    print("2. Building targets...")
    build_cmd = ["bazel", "build"] + TARGETS.split() + [
        "--build_event_json_file=" + JSON_LOG,
        "--curses=no",
        "--color=yes"
    ]
    if EXTRA_FLAGS:
        build_cmd.insert(2, EXTRA_FLAGS)
        
    subprocess.run(build_cmd, check=False)

    # Step 3: Parse the JSON Log
    print("3. Parsing results...")
    successful_targets = set()
    failed_targets = set()
    
    try:
        with open(JSON_LOG, 'r') as f:
            for line in f:
                if not line.strip(): continue
                try:
                    event = json.loads(line)
                    # We look for 'targetCompleted' events
                    if 'id' in event and 'targetCompleted' in event['id']:
                        label = event['id']['targetCompleted']['label']
                        success = event.get('completed', {{}}).get('success', False)
                        
                        if success:
                            successful_targets.add(label)
                        else:
                            failed_targets.add(label)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        print("Warning: JSON log file not found (build might have crashed early).")

    # Step 4: Generate Markdown
    print("4. Writing Markdown report...")
    with open(REPORT_FILE, "w") as f:
        f.write(f"## Bazel Build Report\\n")
        f.write(f"**Date:** {{datetime.datetime.now()}}\\n\\n")
        f.write("| Target | Status | Details |\\n")
        f.write("| :--- | :--- | :--- |\\n")
        
        for target in all_targets:
            if target in successful_targets:
                status = "✅ SUCCESS"
                details = "Build successful"
            elif target in failed_targets:
                status = "❌ FAILED"
                details = "Compilation or Test failed"
            else:
                # If it's in query but not in BEP completed events, it was skipped
                status = "⚪ SKIPPED"
                details = "Dependency failed or not attempted"
            
            f.write(f"| {{target}} | {{status}} | {{details}} |\\n")
            
    print(f"--- Report saved to {{REPORT_FILE}} ---")

if __name__ == "__main__":
    generate_report()
"""

        # 3. Setup Environment
        ctr = self._setup_env(source, bazel_version, ssh_key, ssh_dir, netrc)
        
        # 4. Inject script, run it, and retrieve the report
        return (
            ctr
            .with_new_file("/src/generate_report.py", contents=python_script)
            .with_exec(["python3", "/src/generate_report.py"])
            .file("build_report.md")
        )
        
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