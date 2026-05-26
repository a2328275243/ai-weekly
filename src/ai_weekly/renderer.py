"""Jinja2 template renderer for reports."""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .git_reader import GitSummary

BUILTIN_DIR = Path(__file__).parent / "templates"


def get_env(extra_dirs: list[Path] | None = None) -> Environment:
    """Create Jinja2 environment with built-in + optional user template dirs."""
    dirs = [str(BUILTIN_DIR)]
    if extra_dirs:
        dirs = [str(d) for d in extra_dirs] + dirs
    return Environment(
        loader=FileSystemLoader(dirs),
        autoescape=select_autoescape([]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render(
    summaries: list[GitSummary],
    template_name: str = "default.md.j2",
    extra_vars: dict | None = None,
) -> str:
    """Render summaries through a Jinja2 template."""
    # If user passed a file path, use its parent as loader dir
    template_path = Path(template_name)
    if template_path.suffix == ".j2" and template_path.parent != Path("."):
        env = get_env(extra_dirs=[template_path.parent.resolve()])
        template_name = template_path.name
    else:
        # Append .md.j2 if user just typed "brief"
        if "." not in template_name:
            template_name = f"{template_name}.md.j2"
        env = get_env()

    tmpl = env.get_template(template_name)

    # Compute aggregate stats
    total_commits = sum(len(s.commits) for s in summaries)
    total_files = sum(s.total_files_changed for s in summaries)
    total_ins = sum(s.total_insertions for s in summaries)
    total_del = sum(s.total_deletions for s in summaries)

    ctx = {
        "summaries": summaries,
        "total_commits": total_commits,
        "total_files": total_files,
        "total_insertions": total_ins,
        "total_deletions": total_del,
        **(extra_vars or {}),
    }
    return tmpl.render(**ctx)
