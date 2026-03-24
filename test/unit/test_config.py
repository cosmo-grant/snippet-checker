import re

from pytest import raises

from snippet_checker.config import (
    AnkiConfig,
    DirectoryConfig,
    FieldConfig,
    NoteTypeConfig,
    get_anki_config,
    get_anki_config_path,
    get_directory_config,
    get_directory_config_path,
)


def test_get_directory_config_path_in_given_directory(tmp_path):
    config_file = tmp_path / "snippet_checker.toml"
    config_file.touch()
    assert get_directory_config_path(tmp_path) == config_file


def test_get_directory_config_path_in_parent_directory(tmp_path):
    config_file = tmp_path / "snippet_checker.toml"
    config_file.touch()
    child = tmp_path / "child"
    child.mkdir()
    assert get_directory_config_path(child) == config_file


def test_get_directory_config_path_returns_none_when_no_config(tmp_path):
    assert get_directory_config_path(tmp_path) is None


def test_get_directory_config(tmp_path):
    (tmp_path / "snippet_checker.toml").write_text('[images]\npy = "python:3.13"\n')
    assert get_directory_config(tmp_path) == DirectoryConfig(images={"py": "python:3.13"})


def test_get_anki_config_path(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    xdg_config_dir = tmp_path / "snippet-checker"
    xdg_config_dir.mkdir()
    (xdg_config_dir / "snippet-checker.toml").touch()

    assert get_anki_config_path() == xdg_config_dir / "snippet-checker.toml"


def test_get_anki_config_path_no_xdg_file_but_home_file(tmp_path, monkeypatch):
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

    assert get_anki_config_path() == home_config_dir / "snippet-checker.toml"


def test_get_anki_config_path_no_xdg_config_home_but_home_file(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    fake_home = tmp_path / "home_dir"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    # write a config file in fake home
    home_config_dir = fake_home / ".snippet-checker"
    home_config_dir.mkdir()
    (home_config_dir / "snippet-checker.toml").touch()

    assert get_anki_config_path() == home_config_dir / "snippet-checker.toml"


def test_get_anki_config_path_no_xdg_config_home_and_no_home_file(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    fake_home = tmp_path / "home_dir"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    with raises(Exception, match="^No config found$"):  # FIXME: better error message
        get_anki_config_path()


def test_get_anki_config(monkeypatch, tmp_path):
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
    assert get_anki_config() == AnkiConfig(
        profile="jo",
        note_types=[
            NoteTypeConfig(
                name="code_output",
                code_field=FieldConfig(name="code", pattern=re.compile("code_pattern")),
                output_field=FieldConfig(name="output", pattern=re.compile("output_pattern")),
            ),
        ],
    )


def test_anki_config_exception_if_both_profile_and_path(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    xdg_config_dir = tmp_path / "snippet-checker"
    xdg_config_dir.mkdir()
    (xdg_config_dir / "snippet-checker.toml").write_text("""\
profile = "jo"
collection_path = "/path/to/collection"

[[notes]]
note_type = "code_output"

[notes.code_field]
name = "code"
pattern = "code_pattern"

[notes.output_field]
name = "output"
pattern = "output_pattern"
""")
    with raises(Exception, match="^Cannot set both profile and collection path$"):
        get_anki_config()


def test_anki_config_exception_if_neither_profile_nor_path(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    xdg_config_dir = tmp_path / "snippet-checker"
    xdg_config_dir.mkdir()
    (xdg_config_dir / "snippet-checker.toml").write_text("""\
[[notes]]
note_type = "code_output"

[notes.code_field]
name = "code"
pattern = "code_pattern"

[notes.output_field]
name = "output"
pattern = "output_pattern"
""")
    with raises(Exception, match="^Must set either profile or collection path$"):
        get_anki_config()
