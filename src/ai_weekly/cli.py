"""CLI entry point for ai-weekly."""
from __future__ import annotations

import io
import sys
from datetime import datetime, timedelta
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .ai_generator import AIConfig, generate_report
from .formatters import format_report
from .git_reader import GitError, GitSummary, is_git_repo, read_commits

console = Console()


@click.group(invoke_without_command=True)
@click.version_option()
@click.pass_context
def main(ctx):
    """ai-weekly: generate work reports from git history.

    Just run `ai-weekly` in any git repo to get your weekly report.
    No configuration needed - works out of the box.
    """
    # If no subcommand given, run generate with defaults
    if ctx.invoked_subcommand is None:
        ctx.invoke(generate)


@main.command()
@click.argument("repos", nargs=-1, type=click.Path(exists=True))
@click.option("--since", "-s", default=None, help="Start date YYYY-MM-DD (default: 7 days ago)")
@click.option("--until", "-u", default=None, help="End date YYYY-MM-DD (default: today)")
@click.option("--author", "-a", default=None, help="Filter by git author name")
@click.option("--output", "-o", default=None, help="Save report to file path")
@click.option("--context", "-c", default="", help="Extra context text for AI")
@click.option("--no-ai", is_flag=True, help="Skip AI, use template-based formatting")
@click.option("--format", "fmt", default="markdown", type=click.Choice(["markdown", "feishu", "dingtalk", "json"]), help="Output format")
@click.option("--template", "-t", default="default", help="Template: default|detailed|brief or path/to/file.j2")
@click.option("--github", "github_repo", default=None, is_flag=False, flag_value="auto", help="Pull GitHub PR context (auto-detect or owner/repo)")
@click.option("--preview", is_flag=True, help="Open report in browser preview")
@click.option("--quiet", "-q", is_flag=True, help="Minimal output, no decorations (agent-friendly)")
def generate(repos, since, until, author, output, context, no_ai, fmt, template, github_repo, preview, quiet):
    """Generate a weekly report from git commits.

    Examples:
      ai-weekly generate
      ai-weekly generate ./project-a ./project-b
      ai-weekly generate --since 2026-05-19 --format feishu
      ai-weekly generate --github --no-ai --quiet
    """
    # Default date range: past 7 days
    if since is None:
        since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    if until is None:
        until = datetime.now().strftime("%Y-%m-%d")

    # Validate dates
    for label, val in [("since", since), ("until", until)]:
        try:
            datetime.strptime(val, "%Y-%m-%d")
        except ValueError:
            _err(f"Invalid date for --{label}: {val}. Expected YYYY-MM-DD", quiet)
            raise SystemExit(1)

    since_dt = datetime.strptime(since, "%Y-%m-%d")
    until_dt = datetime.strptime(until, "%Y-%m-%d")

    # Collect repos
    repo_paths = [Path(r) for r in repos] if repos else [Path.cwd()]
    all_summaries: list[GitSummary] = []

    for path in repo_paths:
        path = path.resolve()
        if not is_git_repo(path):
            if not quiet:
                console.print(f"[yellow]SKIP[/yellow] {path} (not a git repo)")
            continue
        try:
            summary = read_commits(path, since=since_dt, until=until_dt, author=author)
        except GitError as e:
            _err(f"{path}: {e}", quiet)
            continue
        if not summary.commits:
            if not quiet:
                console.print(f"[dim]No commits in {summary.repo_name}[/dim]")
            continue
        all_summaries.append(summary)
        if not quiet:
            console.print(f"[green]OK[/green] {summary.repo_name}: {len(summary.commits)} commits")

    if not all_summaries:
        if not quiet:
            console.print("[yellow]No commits found.[/yellow]")
        raise SystemExit(2)

    # GitHub context
    gh_text = ""
    if github_repo:
        gh_text = _fetch_github(github_repo, repo_paths[0], since_dt, until_dt, quiet)
        if gh_text and context:
            context = context + "\n" + gh_text
        elif gh_text:
            context = gh_text

    # Generate report
    config = AIConfig.from_env()
    if no_ai or not config.available:
        if not quiet and not no_ai and not config.available:
            console.print("[dim]No AI configured, using template mode[/dim]")
        report = generate_report(all_summaries, config=AIConfig(), extra_context=context, template=template)
    else:
        if not quiet:
            console.status("Generating with AI...")
        report = generate_report(all_summaries, config=config, extra_context=context, template=template)

    # Format conversion
    formatted = format_report(report, fmt=fmt, summaries=all_summaries)

    # Output
    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(formatted, encoding="utf-8")
        if not quiet:
            console.print(f"[green]Saved to {output}[/green]")
    elif preview:
        _do_preview(report)
    elif quiet or fmt != "markdown":
        click.echo(formatted)
    else:
        console.print(Panel(Markdown(report), title="Weekly Report", border_style="blue"))


@main.command()
@click.argument("file", required=False, type=click.Path(exists=True))
def preview(file):
    """Open a report in browser preview.

    If FILE is given, preview that file. Otherwise generate a fresh report first.
    """
    from .web import start_preview
    from .formatters import to_feishu, to_dingtalk

    if file:
        content = Path(file).read_text(encoding="utf-8")
    else:
        console.print("No file specified. Use: ai-weekly preview report.md")
        raise SystemExit(1)

    start_preview(
        report=content,
        feishu=to_feishu(content),
        dingtalk=to_dingtalk(content),
    )


@main.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def config(as_json):
    """Show current AI configuration status."""
    import json as json_mod
    cfg = AIConfig.from_env()

    if as_json:
        click.echo(json_mod.dumps({
            "base_url": cfg.base_url,
            "api_key_set": bool(cfg.api_key),
            "model": cfg.model,
            "available": cfg.available,
        }, indent=2))
        return

    console.print(Panel.fit("[bold]AI Configuration[/bold]", border_style="blue"))
    console.print(f"  API Base: {cfg.base_url or '(not set)'}")
    console.print(f"  API Key:  {'***' + cfg.api_key[-4:] if cfg.api_key else '(not set)'}")
    console.print(f"  Model:    {cfg.model}")
    console.print()
    if cfg.available:
        console.print("[green]Ready.[/green]")
    else:
        console.print("[yellow]AI not configured. Set env vars:[/yellow]")
        console.print("  AI_API_KEY=your-key")
        console.print("  AI_BASE_URL=https://api.example.com/v1")


# --- helpers ---

def _err(msg: str, quiet: bool):
    if quiet:
        click.echo(f"ERROR: {msg}", err=True)
    else:
        console.print(f"[red]ERROR[/red] {msg}")


def _fetch_github(github_repo: str, first_repo: Path, since_dt, until_dt, quiet) -> str:
    from .github_context import detect_github_repo, fetch_github_context
    if github_repo == "auto":
        github_repo = detect_github_repo(first_repo)
        if not github_repo:
            if not quiet:
                console.print("[yellow]Cannot detect GitHub repo from remote[/yellow]")
            return ""
    if not quiet:
        console.print(f"[dim]Fetching GitHub PRs for {github_repo}...[/dim]")
    ctx = fetch_github_context(github_repo, since_dt, until_dt)
    if ctx.prs:
        if not quiet:
            console.print(f"[green]OK[/green] {len(ctx.prs)} merged PRs found")
        return ctx.to_prompt_text()
    return ""


def _do_preview(report: str):
    from .web import start_preview
    from .formatters import to_feishu, to_dingtalk
    start_preview(report=report, feishu=to_feishu(report), dingtalk=to_dingtalk(report))
