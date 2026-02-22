from enum import Enum
from pathlib import Path

from .output import Output
from .snippet import GoSnippet, NodeSnippet, PythonSnippet, RubySnippet, RustSnippet, Snippet


class Tag(Enum):
    "Question label, used to signal special treatment."

    NO_CHECK_FORMAT = "no_check_format"
    NO_CHECK_OUTPUT = "no_check_output"
    NO_COMPRESS = "no_compress"
    REVIEW = "review"


class Question:
    def __init__(
        self,
        id: int | Path,
        code: str,
        image: str,
        given_output: str,
        check_output: bool,
        check_formatting: bool,
        traceback_verbosity: int,
        compress: bool,
    ):
        self.id = id
        self.image = image
        self.given_output = given_output
        self.compress = compress
        self.snippet: Snippet
        self.output: Output
        if image.startswith("golang"):
            self.snippet = GoSnippet(code, image, traceback_verbosity)
        elif image.startswith("python") or image.startswith("numpy"):
            self.snippet = PythonSnippet(code, image, traceback_verbosity)
        elif image.startswith("node"):
            self.snippet = NodeSnippet(code, image, traceback_verbosity)
        elif image.startswith("ruby"):
            self.snippet = RubySnippet(code, image, traceback_verbosity)
        elif image.startswith("rust"):
            self.snippet = RustSnippet(code, image, traceback_verbosity)
        else:
            raise ValueError(f"Cannot tell language from tag 'image:{image}'")
        self.check_output = check_output
        self.check_formatting = check_formatting

    def has_ok_output(self) -> bool:
        return self.snippet.output.normalised == self.given_output
