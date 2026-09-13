"""
test_run_script_selection — Regression test for run.py's newest-script
selection, guarding against picking a stale file when multiple scripts
match the same jira_id (e.g. across module changes between runs).
Part of: QA Orchestrator
Phase: 2
Mock-safe: yes
"""
import os
import time

from run import find_newest_script


def test_find_newest_script_returns_none_when_no_match(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "outputs" / "e2e").mkdir(parents=True)
    assert find_newest_script("PROJ-999") is None


def test_find_newest_script_picks_most_recently_written_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    stale_dir = tmp_path / "outputs" / "e2e" / "investor" / "dashboard" / "PROJ-123" / "v1"
    stale_dir.mkdir(parents=True)
    stale = stale_dir / "dashboard_PROJ-123_001.spec.py"
    stale.write_text("# stale")
    old_time = time.time() - 3600
    os.utime(stale, (old_time, old_time))

    fresh_dir = tmp_path / "outputs" / "e2e" / "investor" / "login" / "PROJ-123" / "v1"
    fresh_dir.mkdir(parents=True)
    fresh = fresh_dir / "login_PROJ-123_001.spec.py"
    fresh.write_text("# fresh")

    result = find_newest_script("PROJ-123")
    assert result.resolve() == fresh.resolve()
