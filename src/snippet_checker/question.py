from enum import Enum
from pathlib import Path

from .normaliser import OutputNormaliser
from .snippet import Snippet


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
        runner_image: str,
        formatter_image: str,
        given_output: str,
        check_output: bool,
        check_format: bool,
        output_verbosity: int,
        compress: bool,
        timeout: float | None,
        review: bool = False,
    ):
        self.id = id
        self.given_output = given_output
        self.output_verbosity = output_verbosity
        self.compress = compress
        self.timeout = timeout
        self.snippet: Snippet
        self.snippet = Snippet(code, runner_image, formatter_image)
        self.check_output = check_output
        self.check_format = check_format
        self.review = review

    def normalised_actual_output(self):
        actual_output = self.snippet.output(self.timeout)
        return OutputNormaliser.normalise(actual_output, output_verbosity=self.output_verbosity)
