"""Tests for git_reader module."""

import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from ai_weekly.git_reader import (
    GitError,
    GitSummary,
    _extract_number,
    _parse_log_output,
    is_git_repo,
    read_commits,
)


def test_extract_number_files():
    line = " 3 files changed, 42 insertions(+), 10 deletions(-)"
    assert _extract_number(line, "file") == 3
    assert _extract_number(line, "insertion") == 42
    assert _extract_number(line, "deletion") == 10


def test_extract_number_missing_keyword():
    line = " 1 file changed, 5 insertions(+)"
    assert _extract_number(line, "deletion") == 0


def test_extract_number_empty():
    assert _extract_number("", "file") == 0


def test_parse_log_output_empty():
    assert _parse_log_output("") == []
    assert _parse_log_output("   \n  ") == []


def test_parse_log_output_single_commit():
    output = "abc123|Alice|2026-05-20T10:00:00+08:00|feat: add login\n"
    commits = _parse_log_output(output)
    assert len(commits) == 1
    assert commits[0].author == "Alice"
    assert commits[0].message == "feat: add login"


def test_parse_log_output_with_stat():
    output = (
        "abc123|Alice|2026-05-20T10:00:00+08:00|fix: bug\n"
        "\n"
        " 2 files changed, 10 insertions(+), 3 deletions(-)\n"
    )
    commits = _parse_log_output(output)
    assert commits[0].files_changed == 2
    assert commits[0].insertions == 10
    assert commits[0].deletions == 3


def test_is_git_repo_false(tmp_path):
    assert is_git_repo(tmp_path) is False


def test_read_commits_not_a_repo(tmp_path):
    with pytest.raises(GitError, match="Not a git repository"):
        read_commits(tmp_path, since=datetime.now(), until=datetime.now())


def test_read_commits_in_temp_repo():
    """Create a temp git repo and verify commit reading."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Tester"],
            cwd=tmp, capture_output=True,
        )
        (tmp_path / "hello.txt").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=tmp, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: initial commit"],
            cwd=tmp, capture_output=True,
        )

        now = datetime.now()
        summary = read_commits(
            tmp_path,
            since=now - timedelta(days=1),
            until=now + timedelta(days=1),
        )
        assert isinstance(summary, GitSummary)
        assert len(summary.commits) == 1
        assert "initial commit" in summary.commits[0].message
        assert summary.total_files_changed >= 1
