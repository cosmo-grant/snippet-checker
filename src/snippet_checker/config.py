import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .question import Tag


@dataclass
class DirectoryConfig:
    images: dict[str, str] = field(default_factory=dict)
    check_format: bool = True
    check_output: bool = True
    output_verbosity: int = 1
    compress: bool = False
    review: bool = False


def get_directory_config_path(start: Path) -> Path | None:
    current = start.resolve()
    while True:
        candidate = current / "snippet_checker.toml"
        if candidate.exists():
            return candidate
        if current.parent == current:
            return None
        current = current.parent


def get_directory_config(dir: Path) -> DirectoryConfig:
    config_path = get_directory_config_path(dir)
    if config_path is not None:
        with open(config_path, "rb") as f:
            config = DirectoryConfig(**tomllib.load(f))
    else:
        config = DirectoryConfig()

    return config


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
class AnkiConfig:
    """Information required for checking an anki deck."""

    note_types: list[NoteTypeConfig]
    profile: str | None = None
    collection_path: Path | None = None

    def __post_init__(self):
        if self.profile is None and self.collection_path is None:
            raise Exception("Must set either profile or collection path")
        if self.profile is not None and self.collection_path is not None:
            raise Exception("Cannot set both profile and collection path")


def get_anki_config_path() -> Path:
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


def get_anki_config() -> AnkiConfig:
    config_path = get_anki_config_path()
    with open(config_path, "rb") as f:
        raw = tomllib.load(f)

    # extra keys are ignored
    return AnkiConfig(
        profile=raw.get("profile"),
        collection_path=Path(raw["collection_path"]) if "collection_path" in raw else None,
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


class AnkiNoteConfig:
    def __init__(self, tags: list[str]) -> None:
        self.image = next(tag for tag in tags if tag.startswith("image:")).removeprefix("image:")
        self.check_output = Tag.NO_CHECK_OUTPUT.value not in tags
        self.check_format = Tag.NO_CHECK_FORMAT.value not in tags
        try:
            self.output_verbosity = int(next(tag for tag in tags if tag.startswith("output_verbosity:")).removeprefix("output_verbosity:"))
        except StopIteration:
            self.output_verbosity = 0
        self.compress = Tag.NO_COMPRESS.value not in tags
