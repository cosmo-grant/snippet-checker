import re

from pytest import raises

from snippet_checker.config import BaseConfig, FieldConfig, NoteTypeConfig, get_base_config, get_base_config_path


def test_get_base_config(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    xdg_config_dir = tmp_path / "snippet-checker"
    xdg_config_dir.mkdir()
    (xdg_config_dir / "snippet-checker.toml").write_text("""\
profile = "jo"

[[notes]]
note_type = "code_output"

[notes.code_field]
name = "code"
pattern = "code_pattern"

[notes.output_field]
name = "output"
pattern = "output_pattern"
""")
    assert get_base_config() == BaseConfig(
        profile="jo",
        note_types=[
            NoteTypeConfig(
                name="code_output",
                code_field=FieldConfig(name="code", pattern=re.compile("code_pattern")),
                output_field=FieldConfig(name="output", pattern=re.compile("output_pattern")),
            ),
        ],
    )


def test_get_base_config_path(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    xdg_config_dir = tmp_path / "snippet-checker"
    xdg_config_dir.mkdir()
    (xdg_config_dir / "snippet-checker.toml").touch()

    assert get_base_config_path() == xdg_config_dir / "snippet-checker.toml"


def test_get_base_config_path_no_xdg_file_but_home_file(tmp_path, monkeypatch):
    # set up fake xdg_config_home and home
    fake_xdg_config_home = tmp_path / "xdg_config_home_dir"
    fake_xdg_config_home.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(fake_xdg_config_home))
    fake_home = tmp_path / "home_dir"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    # write a config file in fake home
    home_config_dir = fake_home / ".snippet-checker"
    home_config_dir.mkdir()
    (home_config_dir / "snippet-checker.toml").touch()

    assert get_base_config_path() == home_config_dir / "snippet-checker.toml"


def test_get_base_config_path_no_xdg_config_home_but_home_file(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    fake_home = tmp_path / "home_dir"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    # write a config file in fake home
    home_config_dir = fake_home / ".snippet-checker"
    home_config_dir.mkdir()
    (home_config_dir / "snippet-checker.toml").touch()

    assert get_base_config_path() == home_config_dir / "snippet-checker.toml"


def test_get_base_config_path_no_xdg_config_home_and_no_home_file(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    fake_home = tmp_path / "home_dir"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    with raises(Exception, match="^No config found$"):  # FIXME: better error message
        get_base_config_path()
