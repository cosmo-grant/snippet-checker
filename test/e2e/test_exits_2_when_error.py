import subprocess


def test_exits_2_when_internal_error(tmp_path):
    # argparse exits 2 if the user gives a bad command.
    # This tests an error deeper inside the app.
    wrongly_structured_dir = tmp_path / "wrongly_structured_dir"
    wrongly_structured_dir.mkdir()
    (wrongly_structured_dir / "main.py").touch()
    (wrongly_structured_dir / "main.go").touch()
    proc = subprocess.run(
        ["snippet-checker", "output", str(tmp_path)],
        timeout=5,
    )
    assert proc.returncode == 2
