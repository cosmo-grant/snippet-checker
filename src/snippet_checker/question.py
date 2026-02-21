from enum import Enum
from pathlib import Path

from .output import GoOutput, NodeOutput, Output, PythonOutput, RubyOutput, RustOutput
from .snippet import GoSnippet, NodeSnippet, PythonSnippet, RubySnippet, RustSnippet, Snippet


class Tag(Enum):
    "Question label, used to signal special treatment."

    NO_CHECK_FORMATTING = "no_check_formatting"
    NO_CHECK_OUTPUT = "no_check_output"
    REVIEW = "review"


class Question:
    def __init__(self, id: int | Path, code: str, image: str, expected_output: str, check_output: bool, check_formatting: bool):
        self.id = id
        self.image = image
        self.snippet: Snippet
        self.output: Output
        if image.startswith("golang"):
            self.snippet = GoSnippet(code, image)
            self.output = GoOutput(expected_output)
        elif image.startswith("python") or image.startswith("numpy"):
            self.snippet = PythonSnippet(code, image)
            self.output = PythonOutput(expected_output)
        elif image.startswith("node"):
            self.snippet = NodeSnippet(code, image)
            self.output = NodeOutput(expected_output)
        elif image.startswith("ruby"):
            self.snippet = RubySnippet(code, image)
            self.output = RubyOutput(expected_output)
        elif image.startswith("rust"):
            self.snippet = RustSnippet(code, image)
            self.output = RustOutput(expected_output)
        else:
            raise ValueError(f"Cannot tell language from tag 'image:{image}'")
        self.check_output = check_output
        self.check_formatting = check_formatting

    def has_ok_output(self) -> bool:
        return self.snippet.output.normalised == self.output.raw
