from pytest import mark

from snippet_checker.normaliser import NodeOutputNormaliser, PythonOutputNormaliser


class TestPythonOutputNormaliser:
    @mark.parametrize(
        "output_verbosity, expected",
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
    def test_normalise_traceback(self, output_verbosity, expected):
        actual = PythonOutputNormaliser.normalise_traceback(
            "Traceback (most recent call last):\n"
            '  File "<string>", line 1, in <module>\n'
            "    1 / 0\n"
            "    ~~^~~\n"
            "ZeroDivisionError: division by zero\n",
            output_verbosity,
        )

        assert actual == expected

    @mark.parametrize(
        "output_verbosity, expected",
        [
            (0, "SyntaxError: no binding for nonlocal 'x' found\n"),
            (1, "SyntaxError: no binding for nonlocal 'x' found\n"),
            (
                2,
                "  File \"/tmp/main.py\", line 3\n    nonlocal x\n    ^^^^^^^^^^\nSyntaxError: no binding for nonlocal 'x' found\n",
            ),
        ],
    )
    def test_normalise_location_info(self, output_verbosity, expected):
        actual = PythonOutputNormaliser.normalise_location_info(
            "  File \"/tmp/main.py\", line 3\n    nonlocal x\n    ^^^^^^^^^^\nSyntaxError: no binding for nonlocal 'x' found\n",
            output_verbosity,
        )

        assert actual == expected

    def test_normalise_memory_address(self):
        actual = PythonOutputNormaliser.normalise_memory_addresses(
            "<__main__.C object at 0x104cfa450>\n<__main__.D object at 0x104cfa5d0>\n<__main__.C object at 0x104cfa450>\n"
        )
        expected = "<__main__.C object at 0x100>\n<__main__.D object at 0x200>\n<__main__.C object at 0x100>\n"

        assert actual == expected


class TestNodeNormaliser:
    @mark.parametrize(
        "output_verbosity, expected",
        [
            (
                0,
                "ReferenceError: x is not defined\n",
            ),
        ],
    )
    def test_normalise_traceback(self, output_verbosity, expected):
        actual = NodeOutputNormaliser.normalise_traceback(
            "/tmp/main.js:2\n"
            "console.log(x)\n"
            "            ^\n"
            "\n"
            "ReferenceError: x is not defined\n"
            "    at Object.<anonymous> (/tmp/main.js:2:13)\n"
            "    at Module._compile (node:internal/modules/cjs/loader:1804:14)\n"
            "    at Object..js (node:internal/modules/cjs/loader:1936:10)\n"
            "    at Module.load (node:internal/modules/cjs/loader:1525:32)\n"
            "    at Module._load (node:internal/modules/cjs/loader:1327:12)\n"
            "    at TracingChannel.traceSync (node:diagnostics_channel:328:14)\n"
            "    at wrapModuleLoad (node:internal/modules/cjs/loader:245:24)\n"
            "    at Module.executeUserEntryPoint [as runMain] (node:internal/modules/run_main:154:5)\n"
            "    at node:internal/main/run_main_module:33:47\n"
            "\n"
            "Node.js v24.13.1\n",
            output_verbosity,
        )

        assert actual == expected
