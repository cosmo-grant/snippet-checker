import re
import subprocess


def test_check_anki_output_ok(anki_config, anki_collection, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    proc = subprocess.run(
        ["uv", "tool", "run", "snippet-checker", "--anki", "output", "check_me"],
        timeout=120,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    m = re.search(r"Will check (\d+)", proc.stdout)
    num_questions_checked = int(m.group(1))
    assert num_questions_checked > 0


def test_check_anki_format_ok(anki_config, anki_collection, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    proc = subprocess.run(
        ["uv", "tool", "run", "snippet-checker", "--anki", "format", "check_me"],
        timeout=120,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    m = re.search(r"Will check (\d+)", proc.stdout)
    num_questions_checked = int(m.group(1))
    assert num_questions_checked > 0
