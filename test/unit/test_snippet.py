from pytest import mark

from snippet_checker.snippet import to_string


@mark.parametrize(
    "logs, expected",
    [
        (
            [(0.1, b"")],
            "",
        ),
        (
            [(0.1, b"hello\r\n")],
            "hello\n",
        ),
        (
            [(0.1, b"hello\r\nworld\r\n")],
            "hello\nworld\n",
        ),
        (
            [(0.1, b"hello\r\n"), (0.1, b"world\r\n")],
            "hello\nworld\n",
        ),
        (
            [(0.9, b"hello\r\n"), (0.1, b"world\r\n")],
            "<~1s>\nhello\nworld\n",
        ),
        (
            [(0.1, b"hello\r\n"), (3.1, b"world\r\n")],
            "hello\n<~3s>\nworld\n",
        ),
        (
            [(0.9, b"hello\r\n"), (3.1, b"world\r\n")],
            "<~1s>\nhello\n<~3s>\nworld\n",
        ),
    ],
)
def test_to_string(logs, expected):
    assert to_string(logs) == expected
