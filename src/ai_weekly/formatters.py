"""Output format converters: markdown, feishu, dingtalk, json."""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime

from .git_reader import GitSummary


def to_markdown(report: str, **_kw) -> str:
    """Pass-through."""
    return report


def to_json(report: str, summaries: list[GitSummary] | None = None, **_kw) -> str:
    """Structured JSON output for agents and pipelines."""
    data: dict = {"report": report, "generated_at": datetime.now().isoformat()}
    if summaries:
        data["stats"] = {
            "total_commits": sum(len(s.commits) for s in summaries),
            "total_files": sum(s.total_files_changed for s in summaries),
            "total_insertions": sum(s.total_insertions for s in summaries),
            "total_deletions": sum(s.total_deletions for s in summaries),
            "repos": [s.repo_name for s in summaries],
        }
    return json.dumps(data, ensure_ascii=False, indent=2)


def to_feishu(report: str, **_kw) -> str:
    """Convert Markdown report to Feishu interactive card JSON."""
    # Parse title from first ## heading
    title = "周报"
    lines = report.strip().split("\n")
    for line in lines:
        if line.startswith("## "):
            title = line[3:].strip()
            break

    # Build card elements
    elements = []
    for line in lines:
        if line.startswith("## "):
            continue  # skip, used as title
        elif line.startswith("### "):
            elements.append({
                "tag": "markdown",
                "content": f"**{line[4:].strip()}**",
            })
        elif line.strip():
            elements.append({"tag": "markdown", "content": line})

    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue",
            },
            "elements": elements,
        },
    }
    return json.dumps(card, ensure_ascii=False, indent=2)


def to_dingtalk(report: str, **_kw) -> str:
    """Convert to DingTalk webhook message JSON."""
    title = "周报"
    lines = report.strip().split("\n")
    for line in lines:
        if line.startswith("## "):
            title = line[3:].strip()
            break

    msg = {
        "msgtype": "markdown",
        "markdown": {"title": title, "text": report},
    }
    return json.dumps(msg, ensure_ascii=False, indent=2)


FORMAT_MAP = {
    "markdown": to_markdown,
    "feishu": to_feishu,
    "dingtalk": to_dingtalk,
    "json": to_json,
}


def format_report(
    report: str,
    fmt: str = "markdown",
    summaries: list[GitSummary] | None = None,
) -> str:
    """Apply output format conversion."""
    fn = FORMAT_MAP.get(fmt)
    if fn is None:
        raise ValueError(f"Unknown format: {fmt}. Choose from: {list(FORMAT_MAP)}")
    return fn(report, summaries=summaries)
