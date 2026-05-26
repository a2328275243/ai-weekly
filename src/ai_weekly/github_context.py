"""Fetch GitHub PR/Issue context to enrich reports."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import httpx

from .git_reader import _run_git


@dataclass
class PRInfo:
    number: int
    title: str
    state: str
    merged_at: str
    labels: list[str] = field(default_factory=list)


@dataclass
class GitHubContext:
    repo: str
    prs: list[PRInfo] = field(default_factory=list)

    def to_prompt_text(self) -> str:
        """Format as text for AI prompt."""
        if not self.prs:
            return ""
        lines = [f"GitHub PRs ({self.repo}):"]
        for pr in self.prs:
            labels = f" [{', '.join(pr.labels)}]" if pr.labels else ""
            lines.append(f"  - #{pr.number} {pr.title}{labels}")
        return "\n".join(lines)

    def to_section(self) -> str:
        """Format as Markdown section for basic report."""
        if not self.prs:
            return ""
        lines = ["\n### Pull Requests\n"]
        for pr in self.prs:
            lines.append(f"- #{pr.number} {pr.title}")
        return "\n".join(lines)


def detect_github_repo(repo_path: Path) -> str | None:
    """Auto-detect owner/repo from git remote URL."""
    try:
        url = _run_git(["remote", "get-url", "origin"], repo_path).strip()
    except Exception:
        return None

    # Match github.com/owner/repo patterns
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+)", url)
    if m:
        return m.group(1).removesuffix(".git")
    return None


def fetch_github_context(
    repo: str,
    since: datetime,
    until: datetime,
    token: str | None = None,
) -> GitHubContext:
    """Fetch merged PRs from GitHub REST API."""
    token = token or os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    ctx = GitHubContext(repo=repo)

    # Search merged PRs in date range
    query = f"repo:{repo} is:pr is:merged merged:{since:%Y-%m-%d}..{until:%Y-%m-%d}"
    url = "https://api.github.com/search/issues"

    try:
        resp = httpx.get(
            url, params={"q": query, "per_page": 30}, headers=headers, timeout=15
        )
        if resp.status_code != 200:
            return ctx

        for item in resp.json().get("items", []):
            ctx.prs.append(PRInfo(
                number=item["number"],
                title=item["title"],
                state="merged",
                merged_at=item.get("pull_request", {}).get("merged_at", ""),
                labels=[l["name"] for l in item.get("labels", [])],
            ))
    except (httpx.HTTPError, KeyError, ValueError):
        pass  # Graceful degradation

    return ctx
