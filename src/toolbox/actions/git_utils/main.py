import dagger
from dagger import object_type, function, Directory, Container, dag, Doc
from typing import Annotated, Optional
import re

@object_type
class GitUtils:
    """
    Advanced Git utilities for daily automation and CI/CD consistency.
    """

    @function
    def base(self) -> Container:
        """
        Returns a container with git and common utilities installed.
        """
        return (
            dag.container()
            .from_("alpine:latest")
            .with_exec(["apk", "add", "--no-cache", "git", "bash", "openssh-client"])
        )

    @function
    async def commit_lint(
        self,
        source: Annotated[Directory, Doc("The repository directory")],
        commits_count: Annotated[int, Doc("Number of recent commits to check")] = 5
    ) -> str:
        """
        Validates recent commit messages against Conventional Commits pattern.
        """
        pattern = r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?!?: .+"
        
        # Get logs from container
        logs = await (
            self.base()
            .with_mounted_directory("/src", source)
            .with_workdir("/src")
            .with_exec(["git", "log", f"-{commits_count}", "--pretty=format:%s"])
            .stdout()
        )
        
        errors = []
        for line in logs.split('\n'):
            if not re.match(pattern, line):
                errors.append(f"❌ Invalid commit message: '{line}'")
        
        if errors:
            return "\n".join(errors) + "\n\nTip: Use 'type(scope): description' format."
        return "✅ All recent commits follow the convention!"

    @function
    async def changelog(
        self,
        source: Annotated[Directory, Doc("The repository directory")],
        since_tag: Annotated[Optional[str], Doc("Starting tag. If None, uses last tag")] = None
    ) -> str:
        """
        Generates a clean changelog since the specified tag.
        """
        start = since_tag if since_tag else "$(git describe --tags --abbrev=0 2>/dev/null || git rev-list --max-parents=0 HEAD)"
        
        cmd = f"git log {start}..HEAD --oneline --no-merges"
        
        return await (
            self.base()
            .with_mounted_directory("/src", source)
            .with_workdir("/src")
            .with_exec(["sh", "-c", cmd])
            .stdout()
        )

    @function
    async def detect_merged_branches(
        self,
        source: Annotated[Directory, Doc("The repository directory")],
        main_branch: Annotated[str, Doc("The primary branch (main/master)")] = "main"
    ) -> str:
        """
        Identifies local branches that have already been merged into the main branch.
        """
        cmd = f"git branch --merged {main_branch} | grep -v '^*' | grep -v '{main_branch}'"
        
        output = await (
            self.base()
            .with_mounted_directory("/src", source)
            .with_workdir("/src")
            .with_exec(["sh", "-c", cmd])
            .stdout()
        )
        
        if not output.strip():
            return "✨ No merged branches found. Your local repo is clean!"
        return f"🗑️ The following branches can be safely deleted:\n{output}"

    @function
    async def suggest_next_version(
        self,
        source: Annotated[Directory, Doc("The repository directory")]
    ) -> str:
        """
        Analyzes recent commits to suggest the next Semantic Version (SemVer).
        """
        logs = await self.changelog(source)
        
        if "BREAKING CHANGE" in logs or "!" in logs:
            return "🚀 Suggested: MAJOR (Incompatible API changes detected)"
        elif "feat" in logs:
            return "✨ Suggested: MINOR (New features detected)"
        return "🔧 Suggested: PATCH (Only bug fixes or chores detected)"