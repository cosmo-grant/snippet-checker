import re
import subprocess


def test_check_directory_output_ok():
    proc = subprocess.run(
        ["uv", "tool", "run", "snippet-checker", "output", "test/e2e/snippets"],
        timeout=120,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    m = re.search(r"Will check (\d+)", proc.stdout)
    num_questions_checked = int(m.group(1))
    assert num_questions_checked > 0


def test_check_directory_format_ok():
    proc = subprocess.run(
        ["uv", "tool", "run", "snippet-checker", "format", "test/e2e/snippets"],
        timeout=120,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    m = re.search(r"Will check (\d+)", proc.stdout)
    num_questions_checked = int(m.group(1))
    assert num_questions_checked > 0
