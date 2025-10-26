from abc import ABC, abstractmethod
from pathlib import Path

from anki.storage import Collection

from question import Question, Tag


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
    EXTENSIONS = {
        ".py": "python",
        ".go": "go",
    }

    @classmethod
    def extension_from_language(cls, language: str) -> str:  # TODO: enum instead?
        return next(ext for ext, lang in cls.EXTENSIONS.items() if lang == language)

    def __init__(self, dir: Path):
        self.dir = dir

    def get(self) -> list[Question]:
        print(f"Looking for questions in directory '{self.dir}'.")

        questions: list[Question] = []
        for question_dir in self.dir.iterdir():
            snippet_path = next(question_dir.glob("snippet.*"))
            language = self.EXTENSIONS[snippet_path.suffix]
            with open(snippet_path) as f:
                code = f.read()
            with open(question_dir / "output.txt") as f:
                output = f.read()
            try:
                with open(question_dir / "tags.txt") as f:
                    tags = {line.strip() for line in f}
            except FileNotFoundError:
                check_output = True
                check_formatting = True
            else:
                check_output = Tag.NO_CHECK_OUTPUT.value in tags
                check_formatting = Tag.NO_CHECK_FORMATTING.value in tags
            questions.append(Question(question_dir, language, code, output, check_output, check_formatting))

        print(f"Found {len(questions)} questions.")

        return questions

    def fix_output(self, question: Question) -> None:
        "Write the normalised output of the given question's snippet to disk, overwriting the existing output."
        assert isinstance(question.id, Path)
        with open(question.id / "output.txt", "w") as f:
            f.write(question.snippet.output.normalised)

    def fix_formatting(self, question: Question) -> None:
        "Write a formatted version of the given question's snippet to disk, overwriting the existing snippet."
        assert isinstance(question.id, Path)
        formatted = question.snippet.format()
        assert formatted is not None  # we only fix if no error when formatting
        extension = self.extension_from_language(question.language)
        with open(question.id / f"snippet{extension}", "w") as f:
            f.write(formatted)

    def add_tag(self, question: Question, tag: Tag) -> None:
        pass


class AnkiRepository(Repository):
    def __init__(self, tag: str):
        path = Path.home() / "Library/Application Support/Anki2/cosmo/collection.anki2"
        self.collection = Collection(str(path))
        self.tag = tag

    def get(self) -> list[Question]:
        print(f"Looking for notes tagged '{self.tag}'.")
        note_ids = self.collection.find_notes("")
        notes = [self.collection.get_note(id) for id in note_ids]
        self.notes = [note for note in notes if self.tag in note.tags]
        print(f"Found {len(self.notes)} notes.")

        questions: list[Question] = []
        for note in self.notes:
            code, output, _, context = note.fields
            language = "go" if context.startswith("Go") else "python"
            code = self.pre_process(code)
            code = self.html_to_plain(code)
            output = self.html_to_plain(output)
            check_output = Tag.NO_CHECK_OUTPUT.value not in note.tags
            check_format = Tag.NO_CHECK_FORMATTING.value not in note.tags
            id = note.id
            questions.append(Question(id, language, code, output, check_output, check_format))

        return questions

    def fix_output(self, question: Question) -> None:
        "Write the normalised, marked up output of the given question's snippet to the anki database."
        assert isinstance(question.id, int)
        note = self.collection.get_note(question.id)  # type: ignore[arg-type]  # TODO: more systematic type conversion
        note_output = self.escape_html(question.snippet.output.normalised)
        note_output = note_output.replace("\n", "<br>")  # TODO: better to use pre tags probably
        note.fields[1] = note_output
        self.collection.update_note(note)

    def fix_formatting(self, question) -> None:
        "Write a formatted version of the given question's snippet to the anki database."
        assert isinstance(question.id, int)
        formatted = question.snippet.format(compressed=True)  # compressed looks better in anki notes
        assert formatted is not None  # we only fix if no error when formatting
        note = self.collection.get_note(question.id)  # type: ignore[arg-type]  # TODO: more systematic type conversion
        formatted = self.escape_html(formatted)
        formatted = self.post_process(formatted, question.language)
        note.fields[0] = formatted
        self.collection.update_note(note)

    def html_to_plain(self, html: str) -> str:
        """
        Replace html tags or entity names with text equivalents.

        Anki note fields are html.
        Code output notes' output field should have minimal markup.
        Replace this markup with text equivalents, e.g. <br> -> \\n.
        """
        # quotation mark and apostrophe are html reserved characters
        # but in my notes we use " and ' seemingly without issue, not &quot; or &apos;
        # so we don't need to replace those
        # also, some &nbsp; linger, so just clean them ad hoc here
        # TODO: think about where these cleaning methods live
        return html.replace("<br>", "\n").replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ").replace("&amp;", "&")

    def escape_html(self, plain: str) -> str:
        return plain.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def pre_process(self, code: str) -> str:
        return (
            code.removeprefix('<pre><code class="lang-python">').removeprefix('<pre><code class="lang-go">').removesuffix("</code></pre>")
        )

    def post_process(self, code: str, language: str) -> str:
        return f'<pre><code class="lang-{language}">{code}</code></pre>'

    def add_tag(self, question: Question, tag: Tag) -> None:
        "Write a tag to the given question indicating special treatment, e.g. don't check output."
        note = self.collection.get_note(int(question.id))  # type: ignore[arg-type]  # TODO: more systematic type conversion
        note.tags.append(tag.value)
        self.collection.update_note(note)
