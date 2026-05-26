"""Tests for git_reader module."""

import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from ai_weekly.git_reader import read_commits, _parse_stat


def test_parse_stat_insertions():
    line = " 3 files changed, 42 insertions(+), 10 deletions(-)"
    assert _parse_stat(line, "file") == 3
    assert _parse_stat(line, "insertion") == 42
    assert _parse_stat(line, "deletion") == 10


def test_parse_stat_missing():
    line = " 1 file changed, 5 insertions(+)"
    assert _parse_stat(line, "deletion") == 0


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
        # Create a file and commit
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
        assert len(summary.commits) == 1
        assert "initial commit" in summary.commits[0].message
