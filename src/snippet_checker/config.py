import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FieldConfig:
    """Information required for extracting the target text from an anki note field."""

    name: str
    pattern: re.Pattern


@dataclass(frozen=True)
class NoteTypeConfig:
    """Information required for checking an anki note type."""

    name: str
    code_field: FieldConfig
    output_field: FieldConfig


@dataclass(frozen=True)
class BaseConfig:
    """Information required for checking an anki deck."""

    profile: str
    note_types: list[NoteTypeConfig]


def get_base_config_path() -> Path:
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    xdg_config_file = (Path(xdg_config_home) / "snippet-checker" / "snippet-checker.toml") if xdg_config_home is not None else None
    home_config_file = Path(os.environ["HOME"]) / ".snippet-checker" / "snippet-checker.toml"

    if xdg_config_file and xdg_config_file.exists():
        config_path = xdg_config_file
    elif home_config_file.exists():
        config_path = home_config_file
    else:
        raise Exception("No config found")

    return config_path


def get_base_config() -> BaseConfig:
    config_path = get_base_config_path()
    with open(config_path, "rb") as f:
        raw = tomllib.load(f)

    # extra keys are ignored
    return BaseConfig(
        profile=raw["profile"],
        note_types=[
            NoteTypeConfig(
                name=note_config["note_type"],
                code_field=FieldConfig(
                    name=note_config["code_field"]["name"],
                    pattern=re.compile(note_config["code_field"]["pattern"]),
                ),
                output_field=FieldConfig(
                    name=note_config["output_field"]["name"],
                    pattern=re.compile(note_config["output_field"]["pattern"]),
                ),
            )
            for note_config in raw["notes"]
        ],
    )
