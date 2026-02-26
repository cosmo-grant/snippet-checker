from pytest import mark

from snippet_checker.output import PythonOutput


class TestPythonNormalise:
    @mark.parametrize(
        "traceback_verbosity, expected",
        [
            (
                0,
                "ZeroDivisionError: division by zero\n",
            ),
            (
                1,
                "Traceback (most recent call last):\n  ...\nZeroDivisionError: division by zero\n",
            ),
            (
                2,
                "Traceback (most recent call last):\n"
                '  File "<string>", line 1, in <module>\n'
                "    1 / 0\n"
                "    ~~^~~\n"
                "ZeroDivisionError: division by zero\n",
            ),
        ],
    )
    def test_normalise_traceback(self, traceback_verbosity, expected):
        actual = PythonOutput.normalise_traceback(
            "Traceback (most recent call last):\n"
            '  File "<string>", line 1, in <module>\n'
            "    1 / 0\n"
            "    ~~^~~\n"
            "ZeroDivisionError: division by zero\n",
            traceback_verbosity,
        )

        assert actual == expected

    def test_normalise_memory_address(self):
        actual = PythonOutput.normalise_memory_addresses(
            "<__main__.C object at 0x104cfa450>\n<__main__.D object at 0x104cfa5d0>\n<__main__.C object at 0x104cfa450>\n"
        )
        expected = "<__main__.C object at 0x100>\n<__main__.D object at 0x200>\n<__main__.C object at 0x100>\n"

        assert actual == expected
