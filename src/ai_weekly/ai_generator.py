"""AI-powered report generation."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import httpx

from .git_reader import GitSummary

DEFAULT_SYSTEM_PROMPT = """你是一个专业的工作周报撰写助手。根据提供的 Git 提交记录，生成一份结构清晰、语言专业的工作周报。

要求：
1. 将零散的 commit 信息归类整理为 2-5 个主要工作项
2. 每个工作项用一句话概括，突出业务价值而非技术细节
3. 语言简洁专业，适合发给领导/团队
4. 如果有 bug 修复类提交，归类为"问题修复"
5. 如果有文档/测试类提交，归类为"工程优化"
6. 输出格式为 Markdown

输出结构：
## 本周工作总结

### 主要完成
1. [工作项1]
2. [工作项2]
...

### 关键数据
- 提交次数：X
- 修改文件：X
- 代码变更：+X / -X
"""


@dataclass
class AIConfig:
    base_url: str = ""
    api_key: str = ""
    model: str = "gpt-4o-mini"

    @classmethod
    def from_env(cls) -> "AIConfig":
        return cls(
            base_url=os.environ.get("AI_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.environ.get("AI_API_KEY", ""),
            model=os.environ.get("AI_MODEL", "gpt-4o-mini"),
        )


def format_commits_for_ai(summary: GitSummary) -> str:
    """Format git summary into a prompt for AI."""
    lines = [
        f"仓库: {summary.repo_name} (分支: {summary.branch})",
        f"提交数: {len(summary.commits)}",
        f"文件变更: {summary.total_files_changed}",
        f"代码增删: +{summary.total_insertions} / -{summary.total_deletions}",
        "",
        "提交记录:",
    ]
    for c in summary.commits:
        lines.append(f"- [{c.hash[:7]}] {c.message} ({c.author}, {c.date.strftime('%m-%d')})")
    return "\n".join(lines)


def generate_report(
    summaries: list[GitSummary],
    config: AIConfig,
    extra_context: str = "",
) -> str:
    """Call AI API to generate weekly report."""
    if not config.api_key:
        # Fallback: generate a simple report without AI
        return _fallback_report(summaries)

    user_content = ""
    for s in summaries:
        user_content += format_commits_for_ai(s) + "\n\n"
    if extra_context:
        user_content += f"\n补充说明: {extra_context}\n"

    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.3,
    }

    url = config.base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }

    resp = httpx.post(url, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _fallback_report(summaries: list[GitSummary]) -> str:
    """Generate a basic report without AI."""
    lines = ["## 本周工作总结\n", "### 主要完成\n"]
    idx = 1
    for s in summaries:
        for c in s.commits:
            lines.append(f"{idx}. {c.message}")
            idx += 1
    lines.append("\n### 关键数据\n")
    total_commits = sum(len(s.commits) for s in summaries)
    total_files = sum(s.total_files_changed for s in summaries)
    total_ins = sum(s.total_insertions for s in summaries)
    total_del = sum(s.total_deletions for s in summaries)
    lines.append(f"- 提交次数：{total_commits}")
    lines.append(f"- 修改文件：{total_files}")
    lines.append(f"- 代码变更：+{total_ins} / -{total_del}")
    return "\n".join(lines)
