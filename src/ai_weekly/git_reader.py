"""Read and parse Git commit history."""

from __future__ import annotations

import subprocess
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Commit:
    hash: str
    author: str
    date: datetime
    message: str
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0


@dataclass
class GitSummary:
    repo_name: str
    branch: str
    commits: list[Commit] = field(default_factory=list)
    total_files_changed: int = 0
    total_insertions: int = 0
    total_deletions: int = 0


class GitError(Exception):
    """Raised when git operations fail."""


def _check_git_available() -> None:
    if shutil.which("git") is None:
        raise GitError("git not found in PATH. Please install git first.")


def _run_git(args: list[str], cwd: Path) -> str:
    """Run a git command and return stdout. Raises GitError on failure."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        raise GitError(f"git command timed out: git {' '.join(args)}")
    except FileNotFoundError:
        raise GitError("git not found. Please install git first.")

    if result.returncode != 0:
        err = result.stderr.strip()
        raise GitError(f"git {args[0]} failed: {err or 'unknown error'}")
    return result.stdout


def get_repo_name(repo_path: Path) -> str:
    """Get repository name from remote URL or folder name."""
    try:
        url = _run_git(["remote", "get-url", "origin"], repo_path).strip()
        name = url.rstrip("/").split("/")[-1]
        return name.removesuffix(".git")
    except GitError:
        return repo_path.name


def get_current_branch(repo_path: Path) -> str:
    """Get current branch name."""
    try:
        return _run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_path).strip()
    except GitError:
        return "unknown"


def is_git_repo(path: Path) -> bool:
    """Check if path is inside a git repository."""
    try:
        _run_git(["rev-parse", "--git-dir"], path)
        return True
    except GitError:
        return False


def read_commits(
    repo_path: Path,
    since: datetime,
    until: datetime,
    author: str | None = None,
) -> GitSummary:
    """Read git commits within a date range.

    Handles:
    - Merge commits (excluded by default with --no-merges)
    - Empty date ranges (returns empty summary)
    - Non-ASCII commit messages
    - Repos with no remote configured
    """
    _check_git_available()
    repo_path = Path(repo_path).resolve()

    if not is_git_repo(repo_path):
        raise GitError(f"Not a git repository: {repo_path}")

    # Use --no-merges to skip merge commits (they clutter reports)
    cmd = [
        "log", "--no-merges",
        f"--since={since.strftime('%Y-%m-%dT00:00:00')}",
        f"--until={until.strftime('%Y-%m-%dT23:59:59')}",
        "--format=%H|%an|%aI|%s",
        "--shortstat",
    ]
    if author:
        cmd.append(f"--author={author}")

    output = _run_git(cmd, repo_path)
    commits = _parse_log_output(output)

    return GitSummary(
        repo_name=get_repo_name(repo_path),
        branch=get_current_branch(repo_path),
        commits=commits,
        total_files_changed=sum(c.files_changed for c in commits),
        total_insertions=sum(c.insertions for c in commits),
        total_deletions=sum(c.deletions for c in commits),
    )


def _parse_log_output(output: str) -> list[Commit]:
    """Parse git log output into Commit objects."""
    commits: list[Commit] = []
    if not output.strip():
        return commits

    lines = output.strip().split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        parts = line.split("|", 3)
        if len(parts) != 4:
            i += 1
            continue

        try:
            commit = Commit(
                hash=parts[0],
                author=parts[1],
                date=datetime.fromisoformat(parts[2]),
                message=parts[3].strip(),
            )
        except (ValueError, IndexError):
            i += 1
            continue

        # Next non-empty line might be shortstat
        i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i < len(lines) and "changed" in lines[i]:
            stat_line = lines[i].strip()
            commit.files_changed = _extract_number(stat_line, "file")
            commit.insertions = _extract_number(stat_line, "insertion")
            commit.deletions = _extract_number(stat_line, "deletion")
            i += 1

        commits.append(commit)

    return commits


def _extract_number(line: str, keyword: str) -> int:
    """Extract a number preceding a keyword from git shortstat output."""
    for part in line.split(","):
        if keyword in part:
            digits = "".join(c for c in part if c.isdigit())
            if digits:
                return int(digits)
    return 0
