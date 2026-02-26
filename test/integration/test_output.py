from __future__ import annotations

import pytest

from snippet_checker.snippet import GoSnippet, NodeSnippet, PythonSnippet, RubySnippet, RustSnippet


class TestPythonOutput:
    def test_hello(self):
        code = 'print("hello")\n'
        snippet = PythonSnippet(code, "python:3.13", output_verbosity=0)
        assert snippet.output.raw == "hello\n"

    def test_hello_sleep_world(self):
        code = 'import time\n\nprint("hello")\ntime.sleep(1)\nprint("world")\n'
        snippet = PythonSnippet(code, "python:3.13", output_verbosity=0)
        assert snippet.output.raw == "hello\n<~1s>\nworld\n"

    def test_hello_no_newline_sleep_world(self):
        code = 'import time\n\nprint("hello", end="")\ntime.sleep(1)\nprint("world")\n'
        snippet = PythonSnippet(code, "python:3.13", output_verbosity=0)
        assert snippet.output.raw == "<~1s>\nhelloworld\n"

    def test_sleep_hello(self):
        code = 'import time\n\ntime.sleep(1)\nprint("hello")\n'
        snippet = PythonSnippet(code, "python:3.13", output_verbosity=0)
        assert snippet.output.raw == "<~1s>\nhello\n"

    def test_hello_exception(self):
        code = 'print("hello")\nraise Exception'
        snippet = PythonSnippet(code, "python:3.13", output_verbosity=0)
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
        snippet = PythonSnippet(code, "python:3.13", output_verbosity=0)
        assert snippet.output.raw == "hello\n<~3s>\nworld\n"


class TestGoOutput:
    def test_hello(self):
        code = 'package main\nimport "fmt"\nfunc main() { fmt.Println("hello") }\n'
        snippet = GoSnippet(code, "golang:1.24", output_verbosity=0)
        assert snippet.output.raw == "hello\n"


class TestNodeOutput:
    def test_hello(self):
        code = 'console.log("hello");\n'
        snippet = NodeSnippet(code, "node:22", output_verbosity=0)
        assert snippet.output.raw == "hello\n"


class TestRubyOutput:
    def test_hello(self):
        code = 'puts "hello"\n'
        snippet = RubySnippet(code, "ruby:3.4", output_verbosity=0)
        assert snippet.output.raw == "hello\n"


class TestRustOutput:
    def test_hello(self):
        code = 'fn main() { println!("hello"); }\n'
        snippet = RustSnippet(code, "rust:1.84", output_verbosity=0)
        assert snippet.output.raw == "hello\n"
