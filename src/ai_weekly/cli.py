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
from .git_reader import GitError, GitSummary, is_git_repo, read_commits

console = Console()


@click.group()
@click.version_option()
def main():
    """ai-weekly: generate work reports from git history."""
    pass


@main.command()
@click.argument("repos", nargs=-1, type=click.Path(exists=True))
@click.option("--since", "-s", default=None, help="Start date (YYYY-MM-DD)")
@click.option("--until", "-u", default=None, help="End date (YYYY-MM-DD)")
@click.option("--author", "-a", default=None, help="Filter by author name")
@click.option("--output", "-o", default=None, help="Save report to file")
@click.option("--context", "-c", default="", help="Extra context to include")
@click.option("--no-ai", is_flag=True, help="Skip AI, just organize commits")
def generate(repos, since, until, author, output, context, no_ai):
    """Generate a weekly report from git commits."""
    # Default date range: past 7 days
    if since is None:
        since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    if until is None:
        until = datetime.now().strftime("%Y-%m-%d")

    # Validate date format
    for label, val in [("since", since), ("until", until)]:
        try:
            datetime.strptime(val, "%Y-%m-%d")
        except ValueError:
            console.print(f"[red]Invalid date format for --{label}: {val}[/red]")
            console.print("Expected: YYYY-MM-DD")
            raise SystemExit(1)

    since_dt = datetime.strptime(since, "%Y-%m-%d")
    until_dt = datetime.strptime(until, "%Y-%m-%d")

    # Default to current directory
    repo_paths = [Path(r) for r in repos] if repos else [Path.cwd()]

    all_summaries: list[GitSummary] = []
    for path in repo_paths:
        path = path.resolve()
        if not is_git_repo(path):
            console.print(f"[yellow]SKIP[/yellow] {path} (not a git repo)")
            continue
        try:
            summary = read_commits(path, since=since_dt, until=until_dt, author=author)
        except GitError as e:
            console.print(f"[red]ERROR[/red] {path}: {e}")
            continue

        if not summary.commits:
            console.print(f"[dim]No commits in {summary.repo_name} for this period[/dim]")
            continue

        all_summaries.append(summary)
        console.print(f"[green]OK[/green] {summary.repo_name}: {len(summary.commits)} commits")

    if not all_summaries:
        console.print("[yellow]No commits found. Nothing to report.[/yellow]")
        raise SystemExit(0)

    # Generate report
    console.print()
    config = AIConfig.from_env()

    if no_ai or not config.available:
        if not no_ai and not config.available:
            console.print("[dim]No AI API configured, using basic format[/dim]")
        report = generate_report(all_summaries, config=AIConfig(), extra_context=context)
    else:
        with console.status("Generating report with AI..."):
            report = generate_report(all_summaries, config=config, extra_context=context)

    # Output
    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        console.print(f"[green]Saved to {out_path}[/green]")
    else:
        console.print(Panel(Markdown(report), title="Weekly Report", border_style="blue"))


@main.command()
def config():
    """Show current AI configuration status."""
    cfg = AIConfig.from_env()
    console.print(Panel.fit("[bold]AI Configuration[/bold]", border_style="blue"))
    console.print(f"  API Base: {cfg.base_url or '(not set)'}")
    console.print(f"  API Key:  {'***' + cfg.api_key[-4:] if cfg.api_key else '(not set)'}")
    console.print(f"  Model:    {cfg.model}")
    console.print()
    if cfg.available:
        console.print("[green]Ready to use AI generation.[/green]")
    else:
        console.print("[yellow]AI not configured. Set environment variables:[/yellow]")
        console.print("  AI_API_KEY=your-key")
        console.print("  AI_BASE_URL=https://api.example.com/v1")
        console.print("  AI_MODEL=gpt-4o-mini  (optional)")
