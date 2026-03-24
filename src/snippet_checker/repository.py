from __future__ import annotations

import platform
import re
import tomllib
from abc import ABC, abstractmethod
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

import tomli_w
from anki.storage import Collection

from .config import AnkiConfig, AnkiNoteConfig, DirectoryConfig, NoteTypeConfig
from .question import Question, Tag

if TYPE_CHECKING:
    from anki.notes import Note


def note_to_question(note_type_configs: list[NoteTypeConfig], note: Note) -> Question:
    """Convert an Anki note to a Question."""
    note_type_config = next(config for config in note_type_configs if config.name == note.note_type()["name"])  # type: ignore[index]
    fields = dict(zip(note.keys(), note.fields, strict=True))
    code_field = fields[note_type_config.code_field.name]
    output_field = fields[note_type_config.output_field.name]
    code = extract_target(note_type_config.code_field.pattern, code_field)
    output = extract_target(note_type_config.output_field.pattern, output_field)
    tags = [tag.removeprefix("snip:") for tag in note.tags if tag.startswith("snip:")]
    note_config = AnkiNoteConfig(tags)
    return Question(
        note.id,
        code,
        note_config.image,
        output,
        note_config.check_output,
        note_config.check_format,
        note_config.output_verbosity,
        note_config.compress,
    )


class Repository(ABC):
    @abstractmethod
    def get(self) -> list[Question]:
        raise NotImplementedError

    @abstractmethod
    def write_output(self, question: Question, output: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def write_code(self, question: Question, code: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_tag(self, question: Question, tag: Tag) -> None:
        raise NotImplementedError


class DirectoryRepository(Repository):
    def __init__(self, config: DirectoryConfig, dir: Path):
        self.config = config
        self.dir = dir

    def get(self) -> list[Question]:
        print(f"Looking for questions in directory '{self.dir}'.")

        questions: list[Question] = []
        for dirpath, _, _ in self.dir.walk():
            snippet_paths = list(dirpath.glob("snippet.*")) + list(dirpath.glob("main.*"))
            if len(snippet_paths) == 0:
                continue
            elif len(snippet_paths) > 1:
                raise Exception(f"{dirpath} has multiple snippets")
            (snippet_path,) = snippet_paths
            with open(snippet_path) as f:
                code = f.read()

            output_path = dirpath / "output.txt"
            try:
                with open(output_path) as f:
                    output = f.read()
            except FileNotFoundError:
                # create empty, so we can in effect write, not only check, the output
                output_path.touch()
                output = ""

            try:
                with open(dirpath / "snippet_checker.toml", "rb") as f:
                    question_config = tomllib.load(f)
            except FileNotFoundError:
                question_config = {}
            config = DirectoryConfig(**(asdict(self.config) | question_config))

            questions.append(
                Question(
                    id=snippet_path,
                    code=code,
                    image=config.images[snippet_path.suffix.removeprefix(".")],
                    given_output=output,
                    check_output=config.check_output,
                    check_format=config.check_format,
                    output_verbosity=config.output_verbosity,
                    compress=config.compress,
                    review=config.review,
                )
            )

        return questions

    def write_output(self, question: Question, output: str) -> None:
        assert isinstance(question.id, Path)
        (question.id.parent / "output.txt").write_text(output)

    def write_code(self, question: Question, code: str) -> None:
        assert isinstance(question.id, Path)
        question.id.write_text(code)

    def add_tag(self, question: Question, tag: Tag) -> None:
        """Write a tag to snippet_checker.toml in the question's directory.
        The tag indicates special treatment, e.g. don't check output."""
        assert isinstance(question.id, Path)
        config_path = question.id.parent / "snippet_checker.toml"

        try:
            with open(config_path, "rb") as f:
                config = dict(tomllib.load(f))
        except FileNotFoundError:
            config = {}

        if tag == Tag.REVIEW:
            config["review"] = True
        elif tag == Tag.NO_CHECK_OUTPUT:
            config["check_output"] = False
        elif tag == Tag.NO_CHECK_FORMAT:
            config["check_format"] = False
        elif tag == Tag.NO_COMPRESS:
            config["compress"] = False

        with open(config_path, "wb") as f:
            tomli_w.dump(config, f)


class AnkiRepository(Repository):
    def __init__(self, config: AnkiConfig, tag: str):
        assert (config.profile is not None and config.collection_path is None) or (
            config.profile is None and config.collection_path is not None
        )
        if config.profile is not None:
            system = platform.system()
            if system == "Linux":
                path = Path.home() / f".local/share/Anki2/{config.profile}/collection.anki2"
            else:  # mac
                path = Path.home() / f"Library/Application Support/Anki2/{config.profile}/collection.anki2"
        if config.collection_path is not None:
            path = config.collection_path

        self.config = config
        self.collection = Collection(str(path))
        self.tag = tag

    def get(self) -> list[Question]:
        print(f"Looking for notes tagged '{self.tag}'.")
        note_ids = self.collection.find_notes("")
        notes = [self.collection.get_note(id) for id in note_ids]
        self.notes = [note for note in notes if self.tag in note.tags]
        return [note_to_question(self.config.note_types, note) for note in self.notes]

    def write_output(self, question: Question, output: str) -> None:
        "Replace the question's output field target by the given string."
        assert isinstance(question.id, int)
        note = self.collection.get_note(question.id)  # type: ignore[arg-type]  # TODO: more systematic type conversion
        note_type_config = next(config for config in self.config.note_types if config.name == note.note_type()["name"])  # type: ignore[index]
        index = next(i for i, field_name in enumerate(note.keys()) if field_name == note_type_config.output_field.name)
        current = note.fields[index]
        fixed = replace_target(note_type_config.output_field.pattern, current, escape_html(output))
        note.fields[index] = fixed
        self.collection.update_note(note)

    def write_code(self, question, code: str) -> None:
        "Replace the question's code field target by the given string."
        assert isinstance(question.id, int)
        note = self.collection.get_note(question.id)  # type: ignore[arg-type]  # TODO: more systematic type conversion
        note_type_config = next(config for config in self.config.note_types if config.name == note.note_type()["name"])  # type: ignore[index]
        index = next(i for i, field_name in enumerate(note.keys()) if field_name == note_type_config.code_field.name)
        current = note.fields[index]
        fixed = replace_target(note_type_config.code_field.pattern, current, code)
        note.fields[index] = fixed
        self.collection.update_note(note)

    def add_tag(self, question: Question, tag: Tag) -> None:
        "Write a tag to the given question indicating special treatment, e.g. don't check output."
        note = self.collection.get_note(int(question.id))  # type: ignore[arg-type]  # TODO: more systematic type conversion
        note.tags.append("snip:" + tag.value)  # TODO: avoid scattered hard-coded "snip:"
        self.collection.update_note(note)


def unescape_html(html: str) -> str:
    """
    Replace html tags or entity names with text equivalents.

    Anki treats note fields as html, so some characters in the notes are escaped or replaced by html tags.
    Unescape them here, replacing them with their text equivalents, e.g. &lt; becomes <.

    Some of these escapes probably don't occur in the notes, but it does no harm to include them in case.
    """
    return (
        html.replace("<br>", "\n")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&apos;", "'")
        .replace("&quot;", '"')
    )


def escape_html(plain: str) -> str:
    """
    Anki treats note fields as html, so we need to escape some characters.

    I follow the mdn docs rule of thumb: escape &, then <; anything else is optional.
    Note that I escape less than I unescape: liberal in what you accept, conservative in what you emit.
    """
    return plain.replace("&", "&amp;").replace("<", "&lt;")  # order matters


def extract_target(pattern: re.Pattern, raw: str) -> str:
    "Extract the html-unescaped match for the pattern's 'target' group in `raw`."
    m = pattern.search(raw)
    assert m is not None
    return unescape_html(m.group("target"))


def replace_target(pattern: re.Pattern, current: str, target_repl: str) -> str:
    "Replace the match for the pattern's 'target' group in `current` with html-escaped `target_repl`."
    m = pattern.search(current)
    assert m is not None
    start, end = m.span("target")
    return current[:start] + escape_html(target_repl) + current[end:]
