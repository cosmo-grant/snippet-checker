from __future__ import annotations

import pytest

from snippet_checker.snippet import GoSnippet, NodeSnippet, PythonSnippet, RubySnippet, RustSnippet


class TestPythonOutput:
    def test_hello(self):
        code = 'print("hello")\n'
        snippet = PythonSnippet(code, "python:3.13")
        assert snippet.output.raw == "hello\n"

    def test_hello_sleep_world(self):
        code = 'import time\n\nprint("hello")\ntime.sleep(1)\nprint("world")\n'
        snippet = PythonSnippet(code, "python:3.13")
        assert snippet.output.raw == "hello\n<~1s>\nworld\n"

    def test_hello_no_newline_sleep_world(self):
        code = 'import time\n\nprint("hello", end="")\ntime.sleep(1)\nprint("world")\n'
        snippet = PythonSnippet(code, "python:3.13")
        assert snippet.output.raw == "<~1s>\nhelloworld\n"

    def test_sleep_hello(self):
        code = 'import time\n\ntime.sleep(1)\nprint("hello")\n'
        snippet = PythonSnippet(code, "python:3.13")
        assert snippet.output.raw == "<~1s>\nhello\n"

    def test_hello_exception(self):
        code = 'print("hello")\nraise Exception'
        snippet = PythonSnippet(code, "python:3.13")
        assert (
            snippet.output.raw == "hello\n"
            "Traceback (most recent call last):\n"
            '  File "/tmp/main.py", line 2, in <module>\n'
            "    raise Exception\n"
            "Exception\n"
        )

    @pytest.mark.xfail
    def test_hello_no_newline_flush_sleep_world(self):
        code = 'import time\n\nprint("hello", end="", flush=True)\ntime.sleep(3)\nprint("world")\n'
        snippet = PythonSnippet(code, "python:3.13")
        assert snippet.output.raw == "hello\n<~3s>\nworld\n"


class TestGoOutput:
    def test_hello(self):
        code = 'package main\nimport "fmt"\nfunc main() { fmt.Println("hello") }\n'
        snippet = GoSnippet(code, "golang:1.24")
        assert snippet.output.raw == "hello\n"


class TestNodeOutput:
    def test_hello(self):
        code = 'console.log("hello");\n'
        snippet = NodeSnippet(code, "node:22")
        assert snippet.output.raw == "hello\n"

    def test_hello_error(self):
        code = 'console.log("hello");\nconsole.log(x)'
        snippet = NodeSnippet(code, "node:24.13.1")
        assert (
            snippet.output.raw
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
        snippet = RubySnippet(code, "ruby:3.4")
        assert snippet.output.raw == "hello\n"


class TestRustOutput:
    def test_hello(self):
        code = 'fn main() { println!("hello"); }\n'
        snippet = RustSnippet(code, "rust:1.84")
        assert snippet.output.raw == "hello\n"
