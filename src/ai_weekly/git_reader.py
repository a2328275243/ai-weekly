"""Read and parse Git commit history."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
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


def get_repo_name(repo_path: Path) -> str:
    """Get repository name from remote or folder name."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_path, capture_output=True, text=True, check=True,
        )
        url = result.stdout.strip()
        name = url.rstrip("/").split("/")[-1]
        return name.removesuffix(".git")
    except (subprocess.CalledProcessError, IndexError):
        return repo_path.name


def get_current_branch(repo_path: Path) -> str:
    """Get current branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path, capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"


def read_commits(
    repo_path: Path,
    since: datetime,
    until: datetime,
    author: str | None = None,
) -> GitSummary:
    """Read git commits within a date range."""
    repo_path = Path(repo_path).resolve()
    if not (repo_path / ".git").exists():
        raise ValueError(f"Not a git repository: {repo_path}")

    cmd = [
        "git", "log",
        f"--since={since.strftime('%Y-%m-%d')}",
        f"--until={until.strftime('%Y-%m-%d')}",
        "--format=%H|%an|%aI|%s",
        "--shortstat",
    ]
    if author:
        cmd.append(f"--author={author}")

    result = subprocess.run(
        cmd, cwd=repo_path, capture_output=True, text=True, check=True,
    )

    commits: list[Commit] = []
    lines = result.stdout.strip().split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if "|" in line and len(line.split("|")) == 4:
            parts = line.split("|", 3)
            commit = Commit(
                hash=parts[0],
                author=parts[1],
                date=datetime.fromisoformat(parts[2]),
                message=parts[3],
            )
            # Check next line for stat
            if i + 1 < len(lines) and "changed" in lines[i + 1]:
                stat_line = lines[i + 1].strip()
                commit.files_changed = _parse_stat(stat_line, "file")
                commit.insertions = _parse_stat(stat_line, "insertion")
                commit.deletions = _parse_stat(stat_line, "deletion")
                i += 1
            commits.append(commit)
        i += 1

    summary = GitSummary(
        repo_name=get_repo_name(repo_path),
        branch=get_current_branch(repo_path),
        commits=commits,
        total_files_changed=sum(c.files_changed for c in commits),
        total_insertions=sum(c.insertions for c in commits),
        total_deletions=sum(c.deletions for c in commits),
    )
    return summary


def _parse_stat(line: str, keyword: str) -> int:
    """Parse a number from git shortstat line."""
    for part in line.split(","):
        if keyword in part:
            digits = "".join(c for c in part if c.isdigit())
            return int(digits) if digits else 0
    return 0
