import platform
import re
import tomllib
from abc import ABC, abstractmethod
from pathlib import Path

from anki.storage import Collection

from .question import Question, Tag


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
                self.root_config = tomllib.load(f)
        except FileNotFoundError:
            self.root_config = {}

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
            with open(dirpath / "output.txt") as f:
                output = f.read()
            try:
                with open(dirpath / "snippet_checker.toml", "rb") as f:
                    question_config = tomllib.load(f)
            except FileNotFoundError:
                question_config = {}
            config = self.root_config | question_config

            check_output = not config.get(Tag.NO_CHECK_OUTPUT.value, False)  # TODO: simplify
            check_formatting = not config.get(Tag.NO_CHECK_FORMATTING.value, False)
            image = config[snippet_path.suffix.removeprefix(".")]

            questions.append(Question(snippet_path, code, image, output, check_output, check_formatting))

        return questions

    def fix_output(self, question: Question) -> None:
        "Write the normalised output of the given question's snippet to disk, overwriting the existing output."
        assert isinstance(question.id, Path)
        with open(question.id.parent / "output.txt", "w") as f:
            f.write(question.snippet.output.normalised)

    def fix_formatting(self, question: Question) -> None:
        "Write a formatted version of the given question's snippet to disk, overwriting the existing snippet."
        assert isinstance(question.id, Path)
        formatted = question.snippet.format()
        assert formatted is not None  # we only fix if no error when formatting
        with open(question.id, "w") as f:
            f.write(formatted)

    def add_tag(self, question: Question, tag: Tag) -> None:
        pass


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

        questions: list[Question] = []
        for note in self.notes:
            code, output, _, context = note.fields
            image_tags = list(tag for tag in note.tags if tag.startswith("image:"))
            assert len(image_tags) == 1, f"Note {note.id} has {len(image_tags)} image tags. Expected exactly 1."
            image = image_tags[0].removeprefix("image:")
            code = markdown_code(code)
            output = markdown_output(output)
            check_output = Tag.NO_CHECK_OUTPUT.value not in note.tags
            check_format = Tag.NO_CHECK_FORMATTING.value not in note.tags
            id = note.id
            questions.append(Question(id, code, image, output, check_output, check_format))

        return questions

    def fix_output(self, question: Question) -> None:
        "Write the normalised, marked up output of the given question's snippet to the anki database."
        assert isinstance(question.id, int)
        note = self.collection.get_note(question.id)  # type: ignore[arg-type]  # TODO: more systematic type conversion
        output = markup_output(question.snippet.output.normalised)
        note.fields[1] = output
        self.collection.update_note(note)

    def fix_formatting(self, question) -> None:
        "Write a formatted version of the given question's snippet to the anki database."
        assert isinstance(question.id, int)
        formatted = question.snippet.format(compressed=True)  # compressed looks better in anki notes
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
    return plain.replace("&", "&amp;").replace("<", "&lt;")


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
