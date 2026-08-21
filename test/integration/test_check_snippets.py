from snippet_checker.check_snippets import check_formatting, check_output
from snippet_checker.question import Question

from ..fake_repository import FakeRepository


def test_check_output_ok_when_no_formatter_image():
    repo = FakeRepository(
        [
            Question(
                id=0,
                code="",
                runner_image="test-python:3.13",
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
    assert check_output(repo, "check") == 0


def test_check_formatting_ok_when_no_runner_image():
    repo = FakeRepository(
        [
            Question(
                id=0,
                code="",
                runner_image="",
                formatter_image="test-ruff",
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
    assert check_formatting(repo, "check") == 0
