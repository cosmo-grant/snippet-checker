from enum import Enum
from pathlib import Path

from .normaliser import GoOutputNormaliser, NodeOutputNormaliser, OutputNormaliser, PythonOutputNormaliser, RubyOutputNormaliser
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
        check_format: bool,
        output_verbosity: int,
        compress: bool,
        review: bool = False,
    ):
        self.id = id
        self.image = image
        self.given_output = given_output
        self.output_verbosity = output_verbosity
        self.compress = compress
        self.snippet: Snippet
        self.output_normaliser: type[OutputNormaliser]
        if image.startswith("golang"):
            self.snippet = GoSnippet(code, image)
            self.output_normaliser = GoOutputNormaliser
        elif image.startswith("python") or image.startswith("numpy"):
            self.snippet = PythonSnippet(code, image)
            self.output_normaliser = PythonOutputNormaliser
        elif image.startswith("node"):
            self.snippet = NodeSnippet(code, image)
            self.output_normaliser = NodeOutputNormaliser
        elif image.startswith("ruby"):
            self.snippet = RubySnippet(code, image)
            self.output_normaliser = RubyOutputNormaliser
        elif image.startswith("rust"):
            self.snippet = RustSnippet(code, image)
            self.output_normaliser = RubyOutputNormaliser
        else:
            raise ValueError(f"Cannot tell language from image '{image}'")
        self.check_output = check_output
        self.check_format = check_format
        self.review = review

    def normalised_actual_output(self):
        actual_output = self.snippet.output()
        return self.output_normaliser.normalise(actual_output, output_verbosity=self.output_verbosity)
