import platform
import re
import tomllib
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

from anki.storage import Collection

from .question import Question, Tag


@dataclass
class DirectoryConfig:
    images: dict[str, str] = field(default_factory=dict)
    check_formatting: bool = True
    check_output: bool = True
    output_verbosity: int = 1
    compress: bool = False


class AnkiConfig:
    def __init__(self, tags: list[str]) -> None:
        self.image = next(tag for tag in tags if tag.startswith("image:")).removeprefix("image:")
        self.check_output = Tag.NO_CHECK_OUTPUT.value not in tags
        self.check_format = Tag.NO_CHECK_FORMAT.value not in tags
        try:
            self.output_verbosity = int(next(tag for tag in tags if tag.startswith("output_verbosity:")).removeprefix("output_verbosity:"))
        except StopIteration:
            self.output_verbosity = 0
        self.compress = Tag.NO_COMPRESS.value not in tags


class AnkiNote(Protocol):
    """Protocol for Anki note objects. Matches the shape used by anki.notes.Note."""

    @property
    def id(self) -> Any: ...

    @property
    def fields(self) -> list[str]: ...

    @property
    def tags(self) -> list[str]: ...


def note_to_question(note: AnkiNote) -> Question:
    """Convert an Anki note to a Question."""
    code, output, _, _ = note.fields
    code = markdown_code(code)
    output = markdown_output(output)
    tags = [tag.removeprefix("snip:") for tag in note.tags if tag.startswith("snip:")]
    config = AnkiConfig(tags)
    return Question(
        note.id,
        code,
        config.image,
        output,
        config.check_output,
        config.check_format,
        config.output_verbosity,
        config.compress,
    )


class Repository(ABC):
    @abstractmethod
    def get(self) -> list[Question]:
        raise NotImplementedError

    @abstractmethod
    def fix_output(self, question: Question) -> None:
        raise NotImplementedError

    @abstractmethod
    def fix_formatting(self, question: Question) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_tag(self, question: Question, tag: Tag) -> None:
        raise NotImplementedError


class DirectoryRepository(Repository):
    def __init__(self, dir: Path):
        self.dir = dir
        try:
            with open(dir / "snippet_checker.toml", "rb") as f:
                self.root_config = DirectoryConfig(**tomllib.load(f))
        except FileNotFoundError:
            self.root_config = DirectoryConfig()

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
            config = DirectoryConfig(**(asdict(self.root_config) | question_config))

            questions.append(
                Question(
                    id=snippet_path,
                    code=code,
                    image=config.images[snippet_path.suffix.removeprefix(".")],
                    given_output=output,
                    check_output=config.check_output,
                    check_formatting=config.check_formatting,
                    output_verbosity=config.output_verbosity,
                    compress=config.compress,
                )
            )

        return questions

    def fix_output(self, question: Question) -> None:
        "Write the normalised output of the given question's snippet to disk, overwriting the existing output."
        assert isinstance(question.id, Path)
        normalised = question.snippet.output.normalise(question.snippet.output.raw, question.output_verbosity)
        with open(question.id.parent / "output.txt", "w") as f:
            f.write(normalised)

    def fix_formatting(self, question: Question) -> None:
        "Write a formatted version of the given question's snippet to disk, overwriting the existing snippet."
        assert isinstance(question.id, Path)
        formatted = question.snippet.format(compress=question.compress)
        assert formatted is not None  # we only fix if no error when formatting
        with open(question.id, "w") as f:
            f.write(formatted)

    def add_tag(self, question: Question, tag: Tag) -> None:
        pass  # TODO:


class AnkiRepository(Repository):
    def __init__(self, profile: str, tag: str):
        system = platform.system()
        # TODO: pass profile via cli arg or config?
        if system == "Linux":
            path = Path.home() / f".local/share/Anki2/{profile}/collection.anki2"
        else:  # mac
            path = Path.home() / f"Library/Application Support/Anki2/{profile}/collection.anki2"

        self.collection = Collection(str(path))
        self.tag = tag

    def get(self) -> list[Question]:
        print(f"Looking for notes tagged '{self.tag}'.")
        note_ids = self.collection.find_notes("")
        notes = [self.collection.get_note(id) for id in note_ids]
        self.notes = [note for note in notes if self.tag in note.tags]
        return [note_to_question(note) for note in self.notes]

    def fix_output(self, question: Question) -> None:
        "Write the normalised, marked up output of the given question's snippet to the anki database."
        assert isinstance(question.id, int)
        note = self.collection.get_note(question.id)  # type: ignore[arg-type]  # TODO: more systematic type conversion
        normalised = question.snippet.output.normalise(question.snippet.output.raw, question.output_verbosity)
        output = markup_output(normalised)
        note.fields[1] = output
        self.collection.update_note(note)

    def fix_formatting(self, question) -> None:
        "Write a formatted version of the given question's snippet to the anki database."
        assert isinstance(question.id, int)
        formatted = question.snippet.format(compress=question.compress)
        assert formatted is not None  # we only fix if no error when formatting
        note = self.collection.get_note(question.id)  # type: ignore[arg-type]  # TODO: more systematic type conversion
        formatted = markup_code(formatted, question.language)
        note.fields[0] = formatted
        self.collection.update_note(note)

    def add_tag(self, question: Question, tag: Tag) -> None:
        "Write a tag to the given question indicating special treatment, e.g. don't check output."
        note = self.collection.get_note(int(question.id))  # type: ignore[arg-type]  # TODO: more systematic type conversion
        note.tags.append(tag.value)
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


def markdown_code(code: str) -> str:
    "Process an anki code field, which is html, returning source code."
    code = re.sub(r'<pre><code class="lang-\w+">', "", code)
    code = code.removesuffix("</code></pre>")
    code = unescape_html(code)
    return code


def markup_code(code: str, language: str) -> str:
    "Process source code into an anki code field, which is html."
    code = escape_html(code)
    return f'<pre><code class="lang-{language}">{code}</code></pre>'


def markdown_output(output: str) -> str:
    "Process an anki output field, which is html, returning plaintext."
    output = output.removeprefix("<pre><samp>").removesuffix("</samp></pre>")
    output = unescape_html(output)
    return output


def markup_output(output: str) -> str:
    "Process code output into an anki output field, which is html."
    output = escape_html(output)
    return f"<pre><samp>{output}</samp></pre>"
