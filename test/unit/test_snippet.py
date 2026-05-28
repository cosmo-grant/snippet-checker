from pytest import mark

from snippet_checker.snippet import to_string


@mark.parametrize(
    "logs, hanged, expected",
    [
        (
            [(0.1, b"")],
            False,
            "",
        ),
        (
            [(0.1, b"hello\r\n")],
            False,
            "hello\n",
        ),
        (
            [(0.1, b"hello\r\nworld\r\n")],
            False,
            "hello\nworld\n",
        ),
        (
            [(0.1, b"hello\r\n"), (0.1, b"world\r\n")],
            False,
            "hello\nworld\n",
        ),
        (
            [(0.9, b"hello\r\n"), (0.1, b"world\r\n")],
            False,
            "<~1s>\nhello\nworld\n",
        ),
        (
            [(0.1, b"hello\r\n"), (3.1, b"world\r\n")],
            False,
            "hello\n<~3s>\nworld\n",
        ),
        (
            [(0.9, b"hello\r\n"), (3.1, b"world\r\n")],
            False,
            "<~1s>\nhello\n<~3s>\nworld\n",
        ),
        (
            [],
            True,
            "...\n",
        ),
        (
            [(0.1, b"hello\r\n")],
            True,
            "hello\n...\n",
        ),
        (
            [(0.1, b"hello")],
            True,
            "hello\n...\n",
        ),
    ],
)
def test_to_string(logs, hanged, expected):
    assert to_string(logs, hanged) == expected
