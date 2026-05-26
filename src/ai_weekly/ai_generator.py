"""Report generation with optional AI enhancement."""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from .git_reader import GitSummary

SYSTEM_PROMPT = """\
You are a concise technical writer. Given a list of git commits, produce a \
weekly work summary in Chinese (Markdown). Group related commits into 2-5 \
bullet points that emphasize business value over implementation details. \
Keep it under 300 words. Add a short stats section at the end.

Output format:
## 本周工作总结

### 主要完成
1. ...
2. ...

### 关键数据
- 提交次数：N
- 修改文件：N
- 代码变更：+N / -N
"""


@dataclass
class AIConfig:
    base_url: str = ""
    api_key: str = ""
    model: str = "gpt-4o-mini"
    timeout: int = 60

    @classmethod
    def from_env(cls) -> "AIConfig":
        return cls(
            base_url=os.environ.get("AI_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.environ.get("AI_API_KEY", ""),
            model=os.environ.get("AI_MODEL", "gpt-4o-mini"),
            timeout=int(os.environ.get("AI_TIMEOUT", "60")),
        )

    @property
    def available(self) -> bool:
        return bool(self.api_key and self.base_url)


class AIError(Exception):
    """Raised when AI API call fails."""


def build_prompt(summaries: list[GitSummary], extra: str = "") -> str:
    """Format git data into a prompt string."""
    parts = []
    for s in summaries:
        lines = [f"Repo: {s.repo_name} ({s.branch})"]
        for c in s.commits:
            lines.append(f"  - {c.message} [{c.date.strftime('%m-%d')}]")
        parts.append("\n".join(lines))

    text = "\n\n".join(parts)
    if extra:
        text += f"\n\nAdditional context: {extra}"
    return text


def generate_report(
    summaries: list[GitSummary],
    config: AIConfig,
    extra_context: str = "",
) -> str:
    """Generate weekly report. Falls back to basic formatting if AI unavailable."""
    if not config.available:
        return _basic_report(summaries)

    prompt = build_prompt(summaries, extra_context)

    try:
        return _call_ai(config, prompt)
    except AIError:
        # Silently fall back to basic report
        return _basic_report(summaries)


def _call_ai(config: AIConfig, user_content: str) -> str:
    """Call OpenAI-compatible chat completions API."""
    url = config.base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.3,
        "max_tokens": 1500,
    }

    try:
        resp = httpx.post(
            url, json=payload, headers=headers, timeout=config.timeout
        )
    except httpx.TimeoutException:
        raise AIError("API request timed out")
    except httpx.ConnectError:
        raise AIError(f"Cannot connect to {url}")
    except httpx.HTTPError as e:
        raise AIError(f"HTTP error: {e}")

    if resp.status_code != 200:
        raise AIError(f"API returned {resp.status_code}: {resp.text[:200]}")

    try:
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as e:
        raise AIError(f"Unexpected API response format: {e}")


def _basic_report(summaries: list[GitSummary]) -> str:
    """Generate a structured report without AI."""
    total_commits = sum(len(s.commits) for s in summaries)
    total_files = sum(s.total_files_changed for s in summaries)
    total_ins = sum(s.total_insertions for s in summaries)
    total_del = sum(s.total_deletions for s in summaries)

    lines = ["## 本周工作总结\n", "### 主要完成\n"]

    idx = 1
    for s in summaries:
        if len(summaries) > 1:
            lines.append(f"**{s.repo_name}**\n")
        for c in s.commits:
            lines.append(f"{idx}. {c.message}")
            idx += 1
        if len(summaries) > 1:
            lines.append("")

    lines.append("\n### 关键数据\n")
    lines.append(f"- 提交次数: {total_commits}")
    lines.append(f"- 修改文件: {total_files}")
    lines.append(f"- 代码变更: +{total_ins} / -{total_del}")

    if len(summaries) > 1:
        lines.append(f"- 涉及仓库: {', '.join(s.repo_name for s in summaries)}")

    return "\n".join(lines)
