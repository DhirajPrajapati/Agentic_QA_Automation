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
    (tmp_path / "outputs" / "scripts").mkdir(parents=True)
    assert find_newest_script("PROJ-999") is None


def test_find_newest_script_picks_most_recently_written_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    scripts_dir = tmp_path / "outputs" / "scripts"
    scripts_dir.mkdir(parents=True)

    stale = scripts_dir / "investor_dashboard_PROJ-123.py"
    stale.write_text("# stale")
    old_time = time.time() - 3600
    os.utime(stale, (old_time, old_time))

    fresh = scripts_dir / "investor_login_PROJ-123.py"
    fresh.write_text("# fresh")

    result = find_newest_script("PROJ-123")
    assert result.resolve() == fresh.resolve()
