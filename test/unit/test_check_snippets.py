from pytest import raises

from snippet_checker.check_snippets import NoFormatterImageError, NoRunnerImageError, check_formatting, check_output
from snippet_checker.question import Question

from ..fake_repository import FakeRepository


def test_check_output_raises_when_questions_lack_runner_image():
    repo = FakeRepository(
        [
            Question(
                id=0,
                code="",
                runner_image="",
                formatter_image="",
                given_output="",
                check_output=True,
                check_format=True,
                output_verbosity=0,
                compress=False,
                timeout=None,
                review=False,
            )
        ]
    )
    with raises(NoRunnerImageError, match="^Some questions have no runner image: 0$"):
        check_output(repo, "check")


def test_check_formatting_raises_when_questions_lack_formatter_image():
    repo = FakeRepository(
        [
            Question(
                id=0,
                code="",
                runner_image="",
                formatter_image="",
                given_output="",
                check_output=True,
                check_format=True,
                output_verbosity=0,
                compress=False,
                timeout=None,
                review=False,
            )
        ]
    )
    with raises(NoFormatterImageError, match="^Some questions have no formatter image: 0$"):
        check_formatting(repo, "check")
