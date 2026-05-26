"""CLI entry point for ai-weekly."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .ai_generator import AIConfig, generate_report
from .git_reader import read_commits

console = Console(force_terminal=True)


@click.group()
@click.version_option()
def main():
    """AI Weekly — 从 Git 提交记录生成工作周报"""
    pass


@main.command()
@click.argument("repos", nargs=-1, type=click.Path(exists=True))
@click.option("--since", "-s", default=None, help="开始日期 (YYYY-MM-DD)")
@click.option("--until", "-u", default=None, help="结束日期 (YYYY-MM-DD)")
@click.option("--author", "-a", default=None, help="过滤作者")
@click.option("--output", "-o", default=None, help="输出文件路径")
@click.option("--context", "-c", default="", help="补充说明")
@click.option("--no-ai", is_flag=True, help="不使用 AI，仅整理提交记录")
def generate(repos, since, until, author, output, context, no_ai):
    """生成周报。默认读取当前目录最近 7 天的提交。"""
    # Default: current directory
    if not repos:
        repos = (".",)

    # Default date range: last 7 days
    now = datetime.now()
    if until is None:
        until_dt = now
    else:
        until_dt = datetime.strptime(until, "%Y-%m-%d")
    if since is None:
        since_dt = until_dt - timedelta(days=7)
    else:
        since_dt = datetime.strptime(since, "%Y-%m-%d")

    console.print(
        Panel(
            f"[bold]AI Weekly[/bold] — 周报生成中\n"
            f"时间范围: {since_dt.strftime('%Y-%m-%d')} → {until_dt.strftime('%Y-%m-%d')}\n"
            f"仓库数量: {len(repos)}",
            style="blue",
        )
    )

    # Read commits from all repos
    summaries = []
    for repo in repos:
        repo_path = Path(repo).resolve()
        try:
            summary = read_commits(repo_path, since_dt, until_dt, author)
            summaries.append(summary)
            console.print(
                f"  ✓ [green]{summary.repo_name}[/green] — "
                f"{len(summary.commits)} commits"
            )
        except ValueError as e:
            console.print(f"  x [red]{repo}[/red] - {e}")

    if not summaries or all(len(s.commits) == 0 for s in summaries):
        console.print("\n[yellow]⚠ 该时间范围内没有找到提交记录。[/yellow]")
        return

    # Generate report
    if no_ai:
        config = AIConfig(api_key="")
    else:
        config = AIConfig.from_env()

    with console.status("[bold green]正在生成周报..."):
        report = generate_report(summaries, config, context)

    # Output
    if output:
        Path(output).write_text(report, encoding="utf-8")
        console.print(f"\n[green]✓ 周报已保存到: {output}[/green]")
    else:
        console.print("\n")
        console.print(Markdown(report))

    console.print("\n[dim]提示: 设置 AI_API_KEY 和 AI_BASE_URL 环境变量可启用 AI 智能整理[/dim]")


@main.command()
def config():
    """显示当前配置信息。"""
    cfg = AIConfig.from_env()
    console.print(Panel(
        f"AI Base URL: {cfg.base_url}\n"
        f"AI Model:    {cfg.model}\n"
        f"API Key:     {'✓ 已设置' if cfg.api_key else '✗ 未设置'}",
        title="当前配置",
        style="cyan",
    ))


if __name__ == "__main__":
    main()
