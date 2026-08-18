from __future__ import annotations

import pytest

from snippet_checker.snippet import Snippet


class TestPythonOutput:
    def test_hello(self):
        code = 'print("hello")\n'
        snippet = Snippet(code, "test-python:3.13", formatter_image="test-ruff:1.1")
        assert snippet.output(timeout=None) == "hello\n"

    def test_python_hello_sleep_world(self):
        code = 'import time\n\nprint("hello")\ntime.sleep(1)\nprint("world")\n'
        snippet = Snippet(code, "test-python:3.13", formatter_image="test-ruff:1.1")
        assert snippet.output(timeout=None) == "hello\n<~1s>\nworld\n"

    def test_hello_no_newline_sleep_world(self):
        code = 'import time\n\nprint("hello", end="")\ntime.sleep(1)\nprint("world")\n'
        snippet = Snippet(code, "test-python:3.13", formatter_image="test-ruff:1.1")
        assert snippet.output(timeout=None) == "<~1s>\nhelloworld\n"

    def test_sleep_hello(self):
        code = 'import time\n\ntime.sleep(1)\nprint("hello")\n'
        snippet = Snippet(code, "test-python:3.13", formatter_image="test-ruff:1.1")
        assert snippet.output(timeout=None) == "<~1s>\nhello\n"

    def test_hello_exception(self):
        code = 'print("hello")\nraise Exception'
        snippet = Snippet(code, "test-python:3.13", formatter_image="test-ruff:1.1")
        assert (
            snippet.output(timeout=None) == "hello\n"
            "Traceback (most recent call last):\n"
            '  File "/tmp/main.py", line 2, in <module>\n'
            "    raise Exception\n"
            "Exception\n"
        )

    def test_timeout(self):
        code = 'import time\nprint("here")\ntime.sleep(2)'
        snippet = Snippet(code, "test-python:3.13", formatter_image="test-ruff:1.1")
        assert snippet.output(timeout=1) == "here\n...\n"

    @pytest.mark.xfail
    def test_hello_no_newline_flush_sleep_world(self):
        code = 'import time\n\nprint("hello", end="", flush=True)\ntime.sleep(3)\nprint("world")\n'
        snippet = Snippet(code, "test-python:3.13", formatter_image="test-ruff:1.1")
        assert snippet.output(timeout=None) == "hello\n<~3s>\nworld\n"

    # TODO: investigate
    @pytest.mark.xfail
    def test_carriage_return(self):
        code = 'print("foo\\rbar")'
        snippet = Snippet(code, "test-python:3.13", formatter_image="test-ruff:1.1")
        assert snippet.output(timeout=None) == "bar"

    # TODO: investigate
    @pytest.mark.xfail
    def test_unicode_normalization(self):
        code = (
            "from unicodedata import normalize\n"
            's1 = "ca\N{LATIN SMALL LETTER N WITH TILDE}a\n'
            's2 = "can\N{COMBINING TILDE}a\n'
            "print(s1, s2)\n"
        )
        snippet = Snippet(code, "test-python:3.13", formatter_image="test-ruff:1.1")
        assert snippet.output(timeout=None) == "caña caña"


class TestNumpyOutput:
    def test_elementwise_array_comparison(self):
        code = "import numpy as np\na = np.array([10, 20, 30, 40])\nprint((a - 5) < 18)\n"
        snippet = Snippet(code, "test-numpy:2.5", formatter_image="test-ruff:1.1")
        assert snippet.output(timeout=None) == "[ True  True False False]\n"


class TestGoOutput:
    def test_hello(self):
        code = 'package main\nimport "fmt"\nfunc main() { fmt.Println("hello") }\n'
        snippet = Snippet(code, "test-golang:1.25", formatter_image="test-gofmt:1.1")
        assert snippet.output(timeout=None) == "hello\n"


class TestNodeOutput:
    def test_hello(self):
        code = 'console.log("hello");\n'
        snippet = Snippet(code, "test-node:24.13", "test-prettier:1.1")
        assert snippet.output(timeout=None) == "hello\n"

    def test_hello_error(self):
        code = 'console.log("hello");\nconsole.log(x)'
        snippet = Snippet(code, "test-node:24.13", "test-prettier:1.1")
        assert (
            snippet.output(timeout=None)
            == """hello
/tmp/main.js:2
console.log(x)
            ^

ReferenceError: x is not defined
    at Object.<anonymous> (/tmp/main.js:2:13)
    at Module._compile (node:internal/modules/cjs/loader:1804:14)
    at Object..js (node:internal/modules/cjs/loader:1936:10)
    at Module.load (node:internal/modules/cjs/loader:1525:32)
    at Module._load (node:internal/modules/cjs/loader:1327:12)
    at TracingChannel.traceSync (node:diagnostics_channel:328:14)
    at wrapModuleLoad (node:internal/modules/cjs/loader:245:24)
    at Module.executeUserEntryPoint [as runMain] (node:internal/modules/run_main:154:5)
    at node:internal/main/run_main_module:33:47

Node.js v24.13.1
"""
        )


class TestRubyOutput:
    def test_hello(self):
        code = 'puts "hello"\n'
        snippet = Snippet(code, "test-ruby:3.4", "test-rubocop:1.1")
        assert snippet.output(timeout=None) == "hello\n"


class TestRustOutput:
    def test_hello(self):
        code = 'fn main() { println!("hello"); }\n'
        snippet = Snippet(code, "test-rust:1.84", "test-rustfmt:1.1")
        assert snippet.output(timeout=None) == "hello\n"
