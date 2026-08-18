from pytest import mark

from snippet_checker.normaliser import OutputNormaliser


def test_normalise_memory_address():
    actual = OutputNormaliser.normalise(
        "<__main__.C object at 0x104cfa450>\n<__main__.D object at 0x104cfa5d0>\n<__main__.C object at 0x104cfa450>\n",
        0,
    )
    expected = "<__main__.C object at 0x100>\n<__main__.D object at 0x200>\n<__main__.C object at 0x100>\n"

    assert actual == expected


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
def test_normalise_python_traceback(output_verbosity, expected):
    actual = OutputNormaliser.normalise(
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
def test_normalise_python_location_info(output_verbosity, expected):
    actual = OutputNormaliser.normalise(
        "  File \"/tmp/main.py\", line 3\n    nonlocal x\n    ^^^^^^^^^^\nSyntaxError: no binding for nonlocal 'x' found\n",
        output_verbosity,
    )

    assert actual == expected


def test_normalise_python_single_errno():
    actual = OutputNormaliser.normalise("OSError: [Errno 98] Address already in use", 0)
    expected = "OSError: [Errno NN] Address already in use"

    assert actual == expected


def test_normalise_python_multiple_errnos():
    actual = OutputNormaliser.normalise(
        "OSError: [Errno 98] Address already in use\nFileNotFoundError: [Errno 2] No such file or directory: 'foo.txt'",
        0,
    )
    expected = "OSError: [Errno NN] Address already in use\nFileNotFoundError: [Errno NN] No such file or directory: 'foo.txt'"

    assert actual == expected


def test_normalise_go_stack_overflow():
    actual = OutputNormaliser.normalise(
        "runtime: goroutine stack exceeds 1000000000-byte limit\n"
        "runtime: sp=0x17d457460380 stack=[0x17d457460000, 0x17d477460000]\n"
        "fatal error: stack overflow\n"
        "runtime stack:\n"
        "runtime.throw({0x4c615e?, 0x43813a?})\n"
        "	/usr/local/go/src/runtime/panic.go:1229 +0x48 fp=0x17d437413e98 sp=0x17d437413e68 pc=0x4793c8\n"
        "runtime.newstack()\n"
        "	/usr/local/go/src/runtime/stack.go:1178 +0x5fd fp=0x17d437413fc8 sp=0x17d437413e98 pc=0x4610fd\n"
        "runtime.morestack()\n"
        "	/usr/local/go/src/runtime/asm_amd64.s:681 +0x7d fp=0x17d437413fd0 sp=0x17d437413fc8 pc=0x47d71d\n"
        "\n"
        "goroutine 1 gp=0x17d4373181e0 m=9 mp=0x17d437d00808 [running]:\n",
        # actual overflow output is much longer
        0,
    )

    assert actual == "fatal error: stack overflow\n"


def test_normalise_go_panic():
    actual = OutputNormaliser.normalise(
        "panic: runtime error: invalid memory address or nil pointer dereference\n"
        "[signal SIGSEGV: segmentation violation code=0x1 addr=0x0 pc=0x49df56]\n"
        "\n"
        "goroutine 1 [running]:\n"
        "main.main()\n"
        "\t/tmp/overflow/main.go:7 +0x16\n"
        "exit status 2\n",
        0,
    )

    assert actual == "panic: runtime error: invalid memory address or nil pointer dereference\n"


@mark.parametrize(
    "output_verbosity, expected",
    [
        (
            0,
            "ReferenceError: x is not defined\n",
        ),
    ],
)
def test_normalise_node_traceback(output_verbosity, expected):
    actual = OutputNormaliser.normalise(
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
