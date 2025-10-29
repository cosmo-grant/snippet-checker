from enum import Enum
from pathlib import Path

from output import GoOutput, Output, PythonOutput
from snippet import GoSnippet, PythonSnippet, Snippet


class Tag(Enum):
    "Question label, used to signal special treatment."

    NO_CHECK_FORMATTING = "no_check_formatting"
    NO_CHECK_OUTPUT = "no_check_output"
    REVIEW = "review"


class Question:
    def __init__(self, id: int | Path, language: str, code: str, expected_output: str, check_output: bool, check_formatting: bool):
        self.id = id
        self.language = language
        self.snippet: Snippet
        self.output: Output
        if language == "go":
            self.snippet = GoSnippet(code)
            self.output = GoOutput(expected_output)
        elif language == "python":
            self.snippet = PythonSnippet(code)
            self.output = PythonOutput(expected_output)
        else:
            raise ValueError(f"Unsupported language: {language}")
        self.check_output = check_output
        self.check_formatting = check_formatting

    def has_ok_output(self) -> bool:
        return self.snippet.output.normalised == self.output.raw
